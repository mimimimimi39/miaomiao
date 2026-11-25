// QQ 空间（事件驱动版）。
//
// 设计：本模块**不再调用任何第二模型**（独立的 LLM 地址/密钥/模型）。
// - 自动发动态：调度器到点只推一条 nudge 事件，由主模型用 qq_qzone（action=post） 工具发布（content 须由主模型显式给出）。
// - 评论自动回复：收到评论后推一条 nudge 事件，由主模型用 qq_qzone（action=reply） 工具回复。
// 这样动态/评论的内容都由主模型决定，语气与人格一致，且不需要单独的模型配置。

import * as fs from 'node:fs';
import * as path from 'node:path';
import { isIP } from 'node:net';
import type { Logger } from 'cortico/core/types.ts';
import type { QQApi } from './types.ts';
import type { QQIdentity } from './definition.ts';
import type { QZoneConfig } from './config.ts';

export interface QZoneAutoReplyConfig {
  enabled: boolean;
  dailyQuota: number;
  cooldownSec: number;
}

export interface QZoneConfig {
  /** 是否启用 QQ 空间（动态/评论回复）。 */
  enabled: boolean;
  /** 自动冒泡：每 tick 概率发一条动态。 */
  tickSec: number;
  /** 每个 tick 自动发动态的概率（0~1）。 */
  chancePerTick: number;
  /** 每天自动发动态上限（0=不限）。 */
  dailyQuota: number;
  /** 可见权限 ugc_right：1 公开 / 4 好友 / 16 指定人(target_uins) / 64 仅自己 / 128 黑名单。 */
  permission: number;
  /** 动态配图模式。 */
  imageMode: 'none' | 'recent';
  /** 评论回复用的 OneBot action：'auto' 表示用内置正确值（NapCat/SnowLuma 为 'comment_qzone'），也可直接填协议端 action 名。 */
  commentAction: string;
  autoReplyComments: QZoneAutoReplyConfig;
}

export interface QZonePosterOptions {
  cfg: QZoneConfig;
  log: (...a: unknown[]) => void;
  dataDir: string;
  callApi: (action: string, params: Record<string, unknown>) => Promise<{ data?: unknown; error?: string }>;
  getContext: () => string;
  getRecentImageUrl: () => string | null;
  isPaused: () => boolean;
  /** 评论 ingestion：把评论作为外部事件喂给框架（沉淀记忆）。 */
  pushEvent: (e: unknown) => void;
  /** 由 world 注入：把"请主模型发一条动态/回一条评论"的请求交给主模型（事件驱动，不再用第二模型）。 */
  requestLLM: (nudge: string, kind: 'post' | 'reply', meta?: Record<string, unknown>) => void;
  identity: () => QQIdentity;
}

interface QZoneState {
  dailyCount: number;
  replyDailyCount: number;
  day: string;
  lastReplyAt: number;
  lastPosts: Array<{ tid: string; text: string }>;
  repliedComments: string[];
  handledAtComments: string[];
  commentedFeeds: string[];
}

export type QZonePostResult = { ok: true; tid?: string; text?: string } | { ok: false; error: string };

/** 模型提供的远程附图只允许访问公开 HTTP(S) 地址，拒绝本机、私网和云元数据地址。 */
function isPublicImageUrl(value: string): boolean {
  try {
    const u = new URL(value);
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return false;
    if (u.username || u.password) return false;
    const host = u.hostname.replace(/^\[|\]$/g, '').toLowerCase();
    if (!host || host === 'localhost' || host.endsWith('.local') || host.endsWith('.internal') || host.endsWith('.lan')) return false;
    const ipKind = isIP(host);
    if (ipKind === 4) {
      const p = host.split('.').map(Number);
      const [a, b] = p;
      if (a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || a >= 224) return false;
    } else if (ipKind === 6 && (host === '::1' || host.startsWith('fc') || host.startsWith('fd') || host.startsWith('fe8') || host.startsWith('fe9') || host.startsWith('fea') || host.startsWith('feb'))) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

/** get_qzone_msg_detail 返回的单条评论/回复（已规整、剥内联 @ 标记）。 */
export interface QZoneCommentItem {
  commentId: string;
  uin: string;
  name: string;
  time: number;
  content: string;
  replies?: QZoneCommentItem[];
}

/** get_qzone_msg_detail 返回的动态详情（已规整，供模型省 token 消费）。 */
export interface QZonePostDetail {
  tid: string;
  content: string;
  commentNum: number;
  comments: QZoneCommentItem[];
}

export class QZonePoster {
  private readonly cfg: QZoneConfig;
  private readonly log: (...a: unknown[]) => void;
  private readonly dataDir: string;
  private readonly callApi: (action: string, params: Record<string, unknown>) => Promise<{ data?: unknown; error?: string }>;
  private readonly getContext: () => string;
  private readonly getRecentImageUrl: () => string | null;
  private readonly isPaused: () => boolean;
  private readonly pushEvent: (e: unknown) => void;
  private readonly requestLLM: (nudge: string, kind: 'post' | 'reply', meta?: Record<string, unknown>) => void;
  private readonly identity: () => QQIdentity;

  private state: QZoneState = { dailyCount: 0, replyDailyCount: 0, day: '', lastReplyAt: 0, lastPosts: [] };
  private timer?: ReturnType<typeof setInterval>;
  private commentsTimer?: ReturnType<typeof setInterval>;
  private readonly requestedComments = new Map<string, { at: number; tries: number }>();
  private feedsTimer?: ReturnType<typeof setInterval>;
  private autoCommentTimer?: ReturnType<typeof setInterval>;
  private readonly scheduleKey = 'qzone-state.json';

  constructor(opts: QZonePosterOptions) {
    this.cfg = opts.cfg;
    this.log = opts.log;
    this.dataDir = opts.dataDir;
    this.callApi = opts.callApi;
    this.getContext = opts.getContext;
    this.getRecentImageUrl = opts.getRecentImageUrl;
    this.isPaused = opts.isPaused;
    this.pushEvent = opts.pushEvent;
    this.requestLLM = opts.requestLLM;
    this.identity = opts.identity;
    this.load();
  }

  get enabled(): boolean {
    return this.cfg.enabled;
  }

  get scheduled(): boolean {
    return this.cfg.enabled && this.cfg.chancePerTick > 0;
  }

  start(): void {
    if (this.timer) return;
    const sec = Math.max(10, this.cfg.tickSec || 600);
    this.timer = setInterval(() => this.tick().catch((e) => this.log.error('tick error', e)), sec * 1000);
    this.log.info('started', { tickSec: sec });
    // 评论轮询：每 5 分钟检查最近动态有没有新评论，有就请主模型自动回复。
    const pollSec = 600;
    this.commentsTimer = setInterval(
      () => this.pollComments().catch((e) => this.log.error('comment poll error', e)),
      pollSec * 1000,
    );
    this.log.info('comment poll started', { pollSec });
    setTimeout(() => this.pollComments().catch((e) => this.log.error('comment poll error', e)), 60000);
    // 好友动态：每 10 分钟检查 @ 我的评论；并有一定概率自主评论好友动态。
    const feedPollSec = 1800;
    this.feedsTimer = setInterval(
      () => this.pollFeeds().catch((e) => this.log.error('feeds poll error', e)),
      feedPollSec * 1000,
    );
    this.autoCommentTimer = setInterval(
      () => this.autoCommentFeeds().catch((e) => this.log.error('auto comment error', e)),
      feedPollSec * 1000,
    );
    this.log.info('feeds poll started', { feedPollSec });
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
    if (this.commentsTimer) {
      clearInterval(this.commentsTimer);
      this.commentsTimer = undefined;
    }
    if (this.feedsTimer) {
      clearInterval(this.feedsTimer);
      this.feedsTimer = undefined;
    }
    if (this.autoCommentTimer) {
      clearInterval(this.autoCommentTimer);
      this.autoCommentTimer = undefined;
    }
  }

  /** 发动态：content 须由调用方（主模型经 qq_qzone（action=post））显式提供。NapCat/SnowLuma 用扁平 action 名 send_qzone_msg + ugc_right。 */
  async post(opts: { content: string; images?: string[]; topic?: string; permission?: number | string }): Promise<QZonePostResult> {
    if (!this.cfg.enabled) return { ok: false, error: 'QQ 空间未启用（先在控制台开 worlds.qqbot.qzone.enabled）。' };
    const content = (opts.content || '').trim();
    if (!content) return { ok: false, error: '动态内容不能为空：请用 content 给出要发的内容（本扩展不再自动生成动态文本）。' };
    if (this.cfg.dailyQuota > 0 && this.state.dailyCount >= this.cfg.dailyQuota) {
      return { ok: false, error: `今天自动发动态已达上限（${this.cfg.dailyQuota}），请明天再发，或手动发。` };
    }
    const params: Record<string, unknown> = {
      content,
      // 模型提供的附图经白名单过滤；bot 自己收到的本地图片（collectImages）是可信内部来源，不经此过滤。
      images: this.sanitizeImages(opts.images) ?? (this.cfg.imageMode !== 'none' ? this.collectImages() : []),
      // NapCat/SnowLuma 的 send_qzone_msg 用 ugc_right（仅 1/4/16/64/128 合法）；旧的 'qzone.publish' + visible.type(2/8 非法) 会被拒。
      ugc_right: this.resolveUgcRight(opts.permission, this.cfg.permission),
    };
    if (opts.topic) params.topic = opts.topic;
    let raw: unknown;
    try {
      raw = await this.callApi('send_qzone_msg', params);
    } catch (e) {
      return { ok: false, error: `发布失败：${e instanceof Error ? e.message : String(e)}` };
    }
    // driver.callApi 已解包：raw 即 OneBot 返回的 data（send_qzone_msg 成功时为 null，SnowLuma 不返回 tid）。
    const tid = String((raw as { tid?: string } | null)?.tid ?? '');
    this.recordPost(tid, content);
    this.log.info('posted', { tid });
    return { ok: true, tid, text: content };
  }

  /** 解析可见权限：优先用调用方传入的 ugc_right 数字；否则按配置字符串语义映射。 */
  private resolveUgcRight(permArg: unknown, cfgPerm: unknown): number {
    const valid = new Set([1, 4, 16, 64, 128]);
    const map = (v: unknown): number => {
      if (typeof v === 'number' && valid.has(v)) return v;
      if (typeof v === 'string') {
        switch (v) {
          case 'owner': return 64; // 仅自己
          case 'friend':
          case 'admin': return 4;  // 好友
          default: return 1;       // all / 其它 → 公开
        }
      }
      return 1;
    };
    return permArg !== undefined && permArg !== null ? map(permArg) : map(cfgPerm);
  }

  /** 回复评论（由主模型经 qq_qzone（action=reply） 调用）。NapCat/SnowLuma 用 comment_qzone，只能对整个动态发表新评论，不支持按 comment_id 回楼中楼。 */
  async replyComment(commentId: string, text: string, tid?: string, uin?: number): Promise<{ ok: true } | { ok: false; error: string }> {
    if (!text?.trim()) return { ok: false, error: '评论内容为空。' };
    if (!tid) return { ok: false, error: '缺少 tid（动态 id）。' };
    // commentAction 为 'auto' 时用内置正确 action（NapCat/SnowLuma 为 'comment_qzone'）；否则用配置里填的协议端 action 名。
    const action = this.cfg.commentAction && this.cfg.commentAction !== 'auto' ? this.cfg.commentAction : 'comment_qzone';
    try {
      const payload: Record<string, unknown> = { tid, content: text };
      const targetUin = Number(uin);
      if (Number.isFinite(targetUin) && targetUin > 0) payload.target_uin = targetUin;
      if (commentId) payload.comment_id = String(commentId);
      await this.callApi(action, payload);
    } catch (e) {
      return { ok: false, error: `回复失败：${e instanceof Error ? e.message : String(e)}` };
    }
    if (tid && commentId) {
      const key = tid + ':' + commentId;
      if (!this.state.repliedComments.includes(key)) {
        this.state.repliedComments.push(key);
        if (this.state.repliedComments.length > 300) this.state.repliedComments.shift();
        this.save();
      }
    }
    this.log.info('replied comment', { commentId, tid });
    return { ok: true };
  }

  /**
   * 拉取一条动态的详情与全部评论（SnowLuma `get_qzone_msg_detail`；NapCat 不一定提供，失败会返回 error）。
   * @param tid 动态 id（来自 feeds 返回或 post 回执）
   * @param uin 动态作者（贴主）QQ 号，来自 feeds 返回；查好友动态时必传，自家动态可省略。
   */
  async getDetail(tid: string, uin?: number): Promise<{ ok: boolean; detail?: QZonePostDetail; error?: string }> {
    if (!this.cfg.enabled) return { ok: false, error: 'QQ空间未启用' };
    const tidStr = String(tid ?? '').trim();
    if (!tidStr) return { ok: false, error: '缺少 tid（动态 id，来自 feeds 返回）。' };
    const params: Record<string, unknown> = { tid: tidStr };
    const u = Number(uin);
    if (Number.isFinite(u) && u > 0) params.target_uin = u;
    let raw: unknown;
    try {
      raw = await this.callApi('get_qzone_msg_detail', params);
    } catch (e) {
      return { ok: false, error: `获取动态详情失败：${e instanceof Error ? e.message : String(e)}` };
    }
    return { ok: true, detail: QZonePoster.normalizeDetail(raw, tidStr) };
  }

  /** 把 get_qzone_msg_detail 的返回规整成省 token 的结构；字段缺失时给默认值（协议端字段随版本可能变化）。 */
  private static normalizeDetail(raw: unknown, tid: string): QZonePostDetail {
    const d = (raw ?? {}) as Record<string, unknown>;
    const pickItems = (list: unknown): QZoneCommentItem[] => {
      if (!Array.isArray(list)) return [];
      return list.map((it) => {
        const c = (it ?? {}) as Record<string, unknown>;
        const item: QZoneCommentItem = {
          commentId: String(c.comment_id ?? c.commentId ?? ''),
          uin: String(c.uin ?? ''),
          name: String(c.name ?? '').trim(),
          time: Number(c.time ?? 0),
          content: QZonePoster.humanizeAtMarks(String(c.content ?? '')),
        };
        const replies = pickItems(c.replies);
        if (replies.length) item.replies = replies;
        return item;
      });
    };
    return {
      tid: String(d.tid ?? tid),
      content: typeof d.content === 'string' ? d.content : '',
      commentNum: Number(d.comment_num ?? 0),
      comments: pickItems(d.comments),
    };
  }

  /** 把评论里 QQ 空间的内联 @ 标记（@{uin:xxx,nick:yyy,...}）转成可读的 "@yyy(uin:xxx)"，方便模型直接看懂要 @ 谁。 */
  private static humanizeAtMarks(text: string): string {
    return text
      .replace(/@\{[^}]*?uin:([^,}]+)[^}]*?nick:([^,}]+)[^}]*?\}/g, (_m, u, n) => `@${String(n).trim()}(uin:${String(u).trim()})`)
      .replace(/@\{[^}]*?nick:([^,}]+)[^}]*?uin:([^,}]+)[^}]*?\}/g, (_m, n, u) => `@${String(n).trim()}(uin:${String(u).trim()})`);
  }

  async getFeeds(num: number): Promise<{ ok: boolean; feeds?: unknown[]; hasMore?: boolean; error?: string }> {
    if (!this.cfg.enabled) return { ok: false, error: 'QQ空间未启用' };
    // NapCat/SnowLuma 用 get_qzone_feeds，参数为 { page_num, count }。
    let raw: unknown;
    try {
      raw = await this.callApi('get_qzone_feeds', { page_num: 1, count: num });
    } catch (e) {
      return { ok: false, error: `获取动态列表失败：${e instanceof Error ? e.message : String(e)}` };
    }
    // driver.callApi 已解包：raw 即 data（{ feeds, has_more }）；feed 句柄字段是 key（非 tid）。
    const data = (raw ?? {}) as { feeds?: Array<Record<string, unknown>>; has_more?: boolean };
    // 条目含 HTML 片段，剥标签给模型可读文本；tid 映射为 key 供评论/点赞/删除动作定位该动态。
    const feeds = (data.feeds ?? []).filter((f) => Number(f.uin) > 0).map((f) => ({
      tid: f.key,
      uin: f.uin,
      nickname: f.nickname,
      time: f.time,
      appid: f.appid,
      text: (typeof f.content === 'string' && f.content.trim()
        ? f.content
        : typeof f.html === 'string' ? QZonePoster.stripHtml(String(f.html)) : ''
      ).trim().slice(0, 300),
    }));
    return { ok: true, feeds, hasMore: !!data.has_more };
  }

  /** 把 QQ空间动态 feed 的 HTML 片段转成可读纯文本（供模型消费）。 */
  private static stripHtml(html: string): string {
    return html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/(p|div|li)>/gi, '\n')
      .replace(/<[^>]*>/g, '')
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/&lt;/gi, '<')
      .replace(/&gt;/gi, '>')
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n{2,}/g, '\n')
      .trim();
  }

  async delete(tid: string): Promise<{ ok: boolean; error?: string }> {
    // NapCat/SnowLuma 用 delete_qzone_msg。
    try {
      await this.callApi('delete_qzone_msg', { tid });
    } catch (e) {
      return { ok: false, error: `删除失败：${e instanceof Error ? e.message : String(e)}` };
    }
    return { ok: true };
  }

  private collectImages(): string[] {
    if (this.cfg.imageMode === 'none') return [];
    const url = this.getRecentImageUrl();
    return url ? [url] : [];
  }

  /**
   * 校验模型经 qq_qzone(action=post) 提供的附图链接：仅收 http(s):// 与 data: 图片（base64://）；
   * 拒绝 file:// 等本地/任意协议，避免模型借附图把本机任意文件上传出去（纵深防御：
   * world 层已过滤一次，这里作为真正调 API 的边界再挡一道）。
   */
  private sanitizeImages(urls: string[] | undefined): string[] | undefined {
    if (!urls || !urls.length) return undefined;
    // 仅收 http(s):// 与 base64:// / data: 图片数据；拒绝 file:// 等本地/任意协议，避免模型借附图把本机任意文件上传出去。
    return urls.filter(
      (u) =>
        typeof u === 'string' &&
        (isPublicImageUrl(u) || /^base64:\/\//.test(u) || /^data:image\//i.test(u)),
    );
  }

  /** 评论事件：沉淀为外部事件 + 若开启自动回复则请主模型回复。 */
  onEvent(e: { type?: string; data?: Record<string, unknown> }): void {
    const data = (e.data ?? {}) as Record<string, unknown>;
    if (e.type !== 'qq.message.comment.new') return;
    const tid = String(data.tid ?? '');
    const commentId = String(data.commentId ?? '');
    if (!commentId) return;
    const p = data as { text?: string; operatorNick?: string };
    // 1) 把评论作为外部事件喂给框架（沉淀记忆、让 bot「看见」）
    this.pushEvent({
      type: 'qq.qzone.comment',
      origin: 'external',
      source: 'qq',
      senderKey: `qzone:${tid}`,
      text: `QQ空间评论 ${p.operatorNick ? '(' + p.operatorNick + ')' : ''}：${p.text ?? ''}`,
      meta: { conv: `qzone:${tid}`, tid, commentId },
    });
    // 2) 自动回复：事件驱动（请主模型调 qq_qzone（action=reply）），不再用第二模型生成
    if (this.cfg.commentAction !== 'auto' || !this.cfg.autoReplyComments.enabled) return;
    this.rolloverDay();
    const now = Date.now();
    if (now - this.state.lastReplyAt < this.cfg.autoReplyComments.cooldownSec * 1000) return;
    if (this.cfg.autoReplyComments.dailyQuota > 0 && this.state.replyDailyCount >= this.cfg.autoReplyComments.dailyQuota) return;
    this.state.lastReplyAt = now;
    this.state.replyDailyCount += 1;
    this.save();
    // 评论原文（来自任意评论者，不可信）放进 meta；text 只放指令，不含外部内容。
    const nudge = '你的 QQ 空间动态下有一条新评论。请用 qq_qzone（action=reply） 工具回复，自然一句话，可带 emoji，别客套别太长。评论原文、评论者、tid、comment_id 都在事件 meta 里。';
    this.requestLLM(nudge, 'reply', {
      tid,
      commentId,
      operatorNick: p.operatorNick || '对方',
      original: p.text ?? '',
    });
  }

  private async tick(): Promise<void> {
    if (!this.cfg.enabled) return;
    if (this.isPaused()) return;
    this.rolloverDay();
    if (this.cfg.dailyQuota > 0 && this.state.dailyCount >= this.cfg.dailyQuota) return;
    if (Math.random() >= this.cfg.chancePerTick) return;
    const ctx = this.getContext().slice(-3000);
    const nudge =
      '请你以第一人称主动发一条 QQ 空间动态（说说），可用 qq_qzone（action=post） 工具发布。' +
      '内容像你自己真实的朋友圈碎碎念：对最近聊天里某件事/某个人发表真实看法、吐槽、安利或简介，或分享当下心情。' +
      '自然、有梗、带点小情绪，1-3 句最佳，最多不超 100 字，可带少量 emoji，不要客服腔。' +
      '最近聊天的取材放在事件 meta.context 里，可据此发挥。';
    this.requestLLM(nudge, 'post', ctx ? { context: ctx } : {});
  }

  private rolloverDay(): void {
    const d = new Date().toISOString().slice(0, 10);
    if (d !== this.state.day) {
      this.state.day = d;
      this.state.dailyCount = 0;
      this.state.replyDailyCount = 0;
    }
  }

  private recordPost(tid: string, text: string): void {
    this.rolloverDay();
    this.state.dailyCount += 1;
    this.state.lastPosts.unshift({ tid, text });
    if (this.state.lastPosts.length > 10) this.state.lastPosts.pop();
    this.save();
  }

  /** 定时检查自己最近动态的评论，发现新评论就请主模型回复。 */
  private async pollComments(): Promise<void> {
    if (!this.cfg.enabled) return;
    if (this.isPaused()) return;
    if (!this.cfg.autoReplyComments.enabled) return;
    const hour = new Date().getHours();
    if (hour < 8) return;
    if (!this.state.repliedComments) this.state.repliedComments = [];
    const self = String(this.identity()?.selfId ?? '');
    const posts = (this.state.lastPosts || []).slice(0, 2);
    if (!posts.length) return;
    for (const post of posts) {
      if (!post.tid) continue;
      await new Promise((r) => setTimeout(r, 3000));
      const r = await this.getDetail(post.tid).catch((e) => {
        this.log.warn('评论轮询 detail 异常', { tid: post.tid, err: String(e) });
        return null;
      });
      if (!r || !r.ok || !r.detail) {
        this.log.warn('评论轮询 detail 失败', { tid: post.tid, err: r?.error });
        continue;
      }
      const flat: Array<{ c: QZoneCommentItem; parent?: QZoneCommentItem }> = [];
      for (const c of r.detail.comments || []) {
        flat.push({ c });
        for (const rep of c.replies || []) flat.push({ c: rep, parent: c });
      }
      for (const { c, parent } of flat) {
        const cid = String(c.commentId || '');
        const key = post.tid + ':' + cid;
        if (!cid || this.state.repliedComments.includes(key)) continue;
        if (self && String(c.uin) === self) continue;
        // 失败/未成功回复的评论允许重试：30 分钟内不重复请求；最多尝试 3 次，之后放弃不再打扰。
        const state = this.requestedComments.get(key) || { at: 0, tries: 0 };
        if (Date.now() - state.at < 30 * 60 * 1000) continue;
        if (state.tries >= 3) {
          this.state.repliedComments.push(key);
          if (this.state.repliedComments.length > 300) this.state.repliedComments.shift();
          this.save();
          this.log.warn('评论多次回复失败，已放弃', { tid: post.tid, commentId: cid });
          continue;
        }
        state.at = Date.now();
        state.tries += 1;
        this.requestedComments.set(key, state);
        try {
          const rr = (await this.callApi('auto_reply_comment', {
            tid: post.tid,
            target_uin: this.identity()?.selfId,
            comment_id: cid,
            comment_uin: c.uin,
            comment_name: c.name,
            comment_content: c.content,
            parent_content: parent?.content ?? '',
          })) as { status?: string; text?: string } | undefined;
          if (rr && rr.status !== 'failed') {
            this.state.repliedComments.push(key);
            if (this.state.repliedComments.length > 300) this.state.repliedComments.shift();
            this.save();
            this.log.info('已自动回复评论', { tid: post.tid, commentId: cid, text: (rr.text || '').slice(0, 40) });
          } else {
            this.log.warn('自动回复评论失败', { tid: post.tid, commentId: cid, res: String(rr).slice(0, 120) });
          }
        } catch (e) {
          this.log.warn('自动回复评论异常', { tid: post.tid, commentId: cid, err: String(e).slice(0, 120) });
        }
      }
    }
  }

  /** 检查好友动态里 @ 我的评论，请主模型回复。 */
  private async pollFeeds(): Promise<void> {
    if (!this.cfg.enabled) return;
    if (this.isPaused()) return;
    const hour = new Date().getHours();
    if (hour < 8) return;
    if (!this.state.handledAtComments) this.state.handledAtComments = [];
    const self = String(this.identity()?.selfId ?? '');
    const r = await this.getFeeds(5).catch(() => null);
    if (!r || !r.ok || !Array.isArray(r.feeds)) return;
    let checked = 0;
    for (const f of r.feeds as Array<Record<string, unknown>>) {
      if (checked >= 3) break;
      checked += 1;
      await new Promise((res) => setTimeout(res, 4000));
      const tid = String(f.tid ?? '');
      if (!tid || String(f.uin) === self) continue;
      const d = await this.getDetail(tid, Number(f.uin)).catch(() => null);
      if (!d || !d.ok || !d.detail) continue;
      for (const c of d.detail.comments || []) {
        if (String(c.uin) === self) continue;
        const content = String(c.content || '');
        if (!content.includes('@mimi') && !content.includes('@<BOT_QQ>')) continue;
        const cid = String(c.commentId || '');
        const key = tid + ':' + cid;
        if (!cid || this.state.handledAtComments.includes(key)) continue;
        this.state.handledAtComments.push(key);
        if (this.state.handledAtComments.length > 300) this.state.handledAtComments.shift();
        this.save();
        const nudge =
          `【必须执行】好友「${f.nickname ?? f.uin}」的动态下有评论 @ 了你：` +
          `${c.name} 说「${content}」。请立刻用 qq_qzone（action=reply，tid=${tid}，uin=${f.uin}，comment_id=${cid}，content=你的回复）回复 ta，` +
          `1 句话，自然友善，不要暴露主人隐私。`;
        this.requestLLM(nudge, 'reply', { tid, commentId: cid });
        this.log.info('检测到 @ 评论，已请求回复', { tid, commentId: cid });
      }
    }
  }

  /** 按一定概率自主评论好友动态。 */
  private async autoCommentFeeds(): Promise<void> {
    if (!this.cfg.enabled) return;
    if (this.isPaused()) return;
    const hour = new Date().getHours();
    if (hour < 8) return;
    if (!this.state.commentedFeeds) this.state.commentedFeeds = [];
    if (Math.random() > 0.1) return;
    const ownerUin = String((this.cfg as unknown as Record<string, unknown>).owner ?? '<OWNER_QQ>');
    const r = await this.getFeeds(10).catch(() => null);
    if (!r || !r.ok || !Array.isArray(r.feeds)) return;
    const pool = (r.feeds as Array<Record<string, unknown>>).filter((f) => {
      const tid = String(f.tid ?? '');
      return tid && String(f.uin) === ownerUin && !this.state.commentedFeeds.includes(tid);
    });
    if (!pool.length) return;
    const f = pool[Math.floor(Math.random() * pool.length)];
    const tid = String(f.tid);
    const text = String(f.text ?? '').slice(0, 80);
    this.state.commentedFeeds.push(tid);
    if (this.state.commentedFeeds.length > 100) this.state.commentedFeeds.shift();
    this.save();
    const nudge =
      `你刷到了好友「${f.nickname ?? f.uin}」的空间动态：「${text}」。` +
      `请立刻用 qq_qzone（action=reply，tid=${tid}，uin=${f.uin}，content=你的评论）真诚评论一句，` +
      `1 句话，具体、不敷衍、不要暴露主人隐私。`;
    this.requestLLM(nudge, 'reply', { tid });
    this.log.info('自主评论好友动态', { tid });
  }

  status(): { enabled: boolean; dailyQuota: number; dailyCount: number; autoReply: boolean; replyDailyCount: number; lastPosts: Array<{ tid: string; text: string }> } {
    return {
      enabled: this.cfg.enabled,
      dailyQuota: this.cfg.dailyQuota,
      dailyCount: this.state.dailyCount,
      autoReply: this.cfg.commentAction === 'auto' && this.cfg.autoReplyComments.enabled,
      replyDailyCount: this.state.replyDailyCount,
      lastPosts: this.state.lastPosts,
    };
  }

  // ---- 持久化（保留，用于每日配额/冷却判定 + 最近动态展示） ----
  private load(): void {
    try {
      const file = path.join(this.dataDir, this.scheduleKey);
      if (fs.existsSync(file)) {
        const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
        if (typeof raw.dailyCount === 'number') this.state.dailyCount = raw.dailyCount;
        if (typeof raw.replyDailyCount === 'number') this.state.replyDailyCount = raw.replyDailyCount;
        if (typeof raw.day === 'string') this.state.day = raw.day;
        if (typeof raw.lastReplyAt === 'number') this.state.lastReplyAt = raw.lastReplyAt;
        if (Array.isArray(raw.lastPosts)) this.state.lastPosts = raw.lastPosts;
        if (Array.isArray(raw.repliedComments)) this.state.repliedComments = raw.repliedComments;
        if (Array.isArray(raw.handledAtComments)) this.state.handledAtComments = raw.handledAtComments;
        if (Array.isArray(raw.commentedFeeds)) this.state.commentedFeeds = raw.commentedFeeds;
      }
    } catch (e) {
      this.log.warn('load failed', e);
    }
  }

  private save(): void {
    try {
      const file = path.join(this.dataDir, this.scheduleKey);
      fs.mkdirSync(this.dataDir, { recursive: true });
      fs.writeFileSync(file, JSON.stringify(this.state), 'utf8');
    } catch (e) {
      this.log.warn('save failed', e);
    }
  }
}
