"""
QQ 空间网页协议桥接服务
从 NapCat 获取 Cookies，走 user.qzone.qq.com 网页 API。
提供 OneBot 风格的 /call 接口，供 Cortico 插件调用。
"""

import os
import sys

LOG_PATH = os.environ.get(
    "QZONE_LOG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "qzone_web.log"),
)
try:
    os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
    _log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
except Exception:
    _log_file = None


class _Tee:
    def write(self, s):
        try:
            if _log_file is not None:
                _log_file.write(s)
        except Exception:
            pass

    def flush(self):
        try:
            if _log_file is not None:
                _log_file.flush()
        except Exception:
            pass


sys.stdout = _Tee()
sys.stderr = _Tee()
import json
import re

try:
    import json5
except Exception:
    json5 = None
import threading
import time
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
NAPCAT = os.environ.get("QZONE_NAPCAT_URL", "http://127.0.0.1:3000").rstrip("/")
HOST = os.environ.get("QZONE_HOST", "127.0.0.1")
PORT = int(os.environ.get("QZONE_PORT", "8090"))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"

MSG_LIST_URL = "https://user.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6"
COMMENT_URL = "https://user.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_re_feeds"
REPLY_URL = "https://h5.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_re_feeds"
PUBLISH_URL = "https://user.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_publish_v6"
DELETE_URL = "https://h5.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_delete_v6"
FEEDS_URL = "https://user.qzone.qq.com/proxy/domain/ic2.qzone.qq.com/cgi-bin/feeds/feeds3_html_more"
LIKE_URL = "https://user.qzone.qq.com/proxy/domain/w.qzone.qq.com/cgi-bin/likes/internal_dolike_app"

_cache = {"ctx": None, "at": 0.0}
_lock = threading.Lock()


def napcat(action, payload):
    req = urllib.request.Request(
        NAPCAT + "/" + action,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with OPENER.open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def gtk2(skey):
    h = 5381
    for ch in skey:
        h += (h << 5) + ord(ch)
    return str(h & 0x7FFFFFFF)


def get_ctx(force=False):
    with _lock:
        if not force and _cache["ctx"] and time.time() - _cache["at"] < 1800:
            return _cache["ctx"]
        ck = napcat("get_cookies", {"domain": "user.qzone.qq.com"})
        raw = (ck.get("data") or {}).get("cookies") or ""
        c = {k: v.value for k, v in SimpleCookie(raw).items()}
        uin_text = c.get("uin", "0")
        uin = int(uin_text[1:] if uin_text[:1].lower() == "o" else uin_text)
        skey = c.get("skey", "")
        p_skey = c.get("p_skey", "") or skey
        _cache["ctx"] = {"uin": uin, "skey": skey, "p_skey": p_skey, "gtk": gtk2(p_skey)}
        _cache["at"] = time.time()
        return _cache["ctx"]


def parse_jsonp(text):
    m = re.search(r"callback\s*\(\s*(\{.*\})\s*\)", text, re.I | re.S)
    if m:
        js = m.group(1)
    else:
        s = text.find("{")
        e = text.rfind("}")
        js = text[s:e + 1] if s != -1 and e > s else ""
    js = js.replace("undefined", "null")
    try:
        return json.loads(js)
    except Exception:
        pass
    if json5 is not None:
        try:
            v = json5.loads(js)
            if isinstance(v, dict):
                return v
        except Exception:
            pass
    return {}


def http_get(url, params, ctx):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url + "?" + q,
        headers={
            "User-Agent": UA,
            "referer": "https://user.qzone.qq.com/%d" % ctx["uin"],
            "origin": "https://user.qzone.qq.com",
            "Cookie": "uin=o%d; skey=%s; p_skey=%s" % (ctx["uin"], ctx["skey"], ctx["p_skey"]),
        },
    )
    with OPENER.open(req, timeout=25) as r:
        return parse_jsonp(r.read().decode("utf-8", "replace"))


def http_post(url, params, data, ctx):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url + "?" + q,
        data=urllib.parse.urlencode(data).encode(),
        headers={
            "User-Agent": UA,
            "referer": "https://user.qzone.qq.com/%d" % ctx["uin"],
            "origin": "https://user.qzone.qq.com",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Cookie": "uin=o%d; skey=%s; p_skey=%s" % (ctx["uin"], ctx["skey"], ctx["p_skey"]),
        },
        method="POST",
    )
    with OPENER.open(req, timeout=25) as r:
        return parse_jsonp(r.read().decode("utf-8", "replace"))


def _norm_comment(c):
    if not isinstance(c, dict):
        return None
    reps = []
    for r in (c.get("replies") or c.get("replyList") or []):
        nr = _norm_comment(r)
        if nr:
            reps.append(nr)
    return {
        "comment_id": str(c.get("tid") or c.get("commentid") or ""),
        "uin": str(c.get("uin") or ""),
        "name": c.get("name") or "",
        "content": c.get("content") or "",
        "time": c.get("createTime") or c.get("createtime") or 0,
        "replies": reps,
    }


def normalize_comments(commentlist):
    out = []
    for c in commentlist or []:
        nc = _norm_comment(c)
        if nc:
            out.append(nc)
    return out


def own_posts(num=5):
    ctx = get_ctx()
    d = http_get(MSG_LIST_URL, {
        "g_tk": ctx["gtk"], "uin": ctx["uin"], "ftype": 0, "sort": 0, "pos": 0,
        "num": num, "replynum": 100, "callback": "_preloadCallback",
        "code_version": 1, "format": "json", "need_comment": 1, "need_private_comment": 1,
    }, ctx)
    return d.get("msglist") or []


def action_detail(params):
    tid = str(params.get("tid") or "")
    ctx = get_ctx()
    posts = own_posts(8)
    for p in posts:
        if str(p.get("tid")) == tid:
            return {
                "status": "ok", "retcode": 0,
                "data": {
                    "tid": tid,
                    "content": p.get("content") or "",
                    "comment_num": len(p.get("commentlist") or []),
                    "comments": normalize_comments(p.get("commentlist")),
                },
            }
    # 不是自己的动态：用 detail API
    d = http_get("https://h5.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msgdetail_v6", {
        "uin": params.get("target_uin") or params.get("uin") or ctx["uin"],
        "tid": tid, "format": "jsonp", "g_tk": ctx["gtk"],
    }, ctx)
    return {
        "status": "ok", "retcode": 0,
        "data": {
            "tid": tid,
            "content": d.get("content") or d.get("content2") or "",
            "comment_num": len(d.get("commentlist") or []),
            "comments": normalize_comments(d.get("commentlist")),
        },
    }


def find_comment(tid, comment_id):
    for p in own_posts(10):
        if str(p.get("tid")) == tid:
            stack = list(p.get("commentlist") or [])
            while stack:
                c = stack.pop()
                if not isinstance(c, dict):
                    continue
                if str(c.get("tid")) == str(comment_id):
                    return c
                stack.extend(c.get("replies") or c.get("replyList") or [])
    return None


def action_comment(params):
    if params.get("comment_id"):
        return action_reply(params)
    ctx = get_ctx()
    tid = str(params.get("tid") or "")
    host = str(params.get("target_uin") or params.get("uin") or ctx["uin"])
    content = str(params.get("content") or "")
    if not tid or not content:
        return {"status": "failed", "retcode": 400, "message": "tid/content 不能为空"}
    try:
        d = http_post(COMMENT_URL, {"g_tk": ctx["gtk"]}, {
            "topicId": "%s_%s__1" % (host, tid), "uin": ctx["uin"], "hostUin": host,
            "feedsType": 100, "inCharset": "utf-8", "outCharset": "utf-8",
            "plat": "qzone", "source": "ic", "platformid": 52, "format": "fs",
            "ref": "feeds", "content": content,
        }, ctx)
        if d.get("code") == 0:
            return {"status": "ok", "retcode": 0, "data": {"comment_id": ""}}
        return {"status": "failed", "retcode": 200, "message": "空间拒绝: code=%s" % d.get("code")}
    except Exception as e:
        return {"status": "failed", "retcode": 500, "message": str(e)[:200]}


def action_reply(params):
    ctx = get_ctx()
    tid = str(params.get("tid") or "")
    comment_id = str(params.get("comment_id") or "")
    content = str(params.get("content") or "")
    host = str(params.get("target_uin") or params.get("uin") or ctx["uin"])
    if not tid or not comment_id or not content:
        return {"status": "failed", "retcode": 400, "message": "tid/comment_id/content 不能为空"}
    c = find_comment(tid, comment_id)
    if not c:
        return {"status": "failed", "retcode": 404, "message": "找不到该评论"}
    try:
        d = http_post(REPLY_URL, {"g_tk": ctx["gtk"]}, {
            "topicId": "%s_%s__1" % (host, tid), "uin": ctx["uin"], "hostUin": host,
            "feedsType": 100, "inCharset": "utf-8", "outCharset": "utf-8",
            "plat": "qzone", "source": "ic", "platformid": 52, "format": "fs",
            "ref": "feeds", "content": content,
            "commentId": str(c.get("tid")), "commentUin": str(c.get("uin")),
            "richval": "", "richtype": "", "private": "0", "paramstr": "2",
            "qzreferrer": "https://user.qzone.qq.com/%d/main" % ctx["uin"],
        }, ctx)
        if d.get("code") == 0:
            return {"status": "ok", "retcode": 0, "data": {"comment_id": ""}}
        # 回复接口被风控时，回退为「对整条动态评论」，内容里 @ 对方。
        name = str(c.get("name") or "")
        fallback = (("@%s " % name) if name else "") + content
        fallback = fallback[:120]
        try:
            d2 = http_post(COMMENT_URL, {"g_tk": ctx["gtk"]}, {
                "topicId": "%s_%s__1" % (host, tid), "uin": ctx["uin"], "hostUin": host,
                "feedsType": 100, "inCharset": "utf-8", "outCharset": "utf-8",
                "plat": "qzone", "source": "ic", "platformid": 52, "format": "fs",
                "ref": "feeds", "content": fallback,
            }, ctx)
            if d2.get("code") == 0:
                return {"status": "ok", "retcode": 0, "data": {"comment_id": "", "fallback": True}}
            return {"status": "failed", "retcode": 200, "message": "回复和评论都被拒: %s / %s" % (d.get("code"), d2.get("code"))}
        except Exception as e2:
            return {"status": "failed", "retcode": 500, "message": str(e2)[:200]}
    except Exception as e:
        return {"status": "failed", "retcode": 500, "message": str(e)[:200]}


def action_feeds(params):
    ctx = get_ctx()
    num = int(params.get("count") or params.get("num") or 5)
    d = http_get(FEEDS_URL, {
        "uin": ctx["uin"], "scope": 0, "view": 1, "filter": "all", "flag": 1,
        "applist": "all", "pagenum": 1, "aisortEndTime": 0, "aisortOffset": 0,
        "aisortBeginTime": 0, "begintime": 0, "format": "json", "g_tk": ctx["gtk"],
        "callback": "_Callback", "count": num,
    }, ctx)
    data_obj = d.get("data") or {}
    items = data_obj.get("data") if isinstance(data_obj, dict) else None
    if items is None:
        items = d.get("data_list") or []
    feeds = []
    for f in items if isinstance(items, list) else []:
        if not isinstance(f, dict):
            continue
        key = f.get("key") or f.get("tid") or ""
        uin = f.get("uin") or 0
        if str(uin) == "0" or not key:
            continue
        feeds.append({
            "key": str(key), "tid": str(key), "uin": str(uin),
            "nickname": f.get("nickname") or f.get("name") or "",
            "html": f.get("html") or f.get("content") or "",
            "time": f.get("time") or 0,
        })
    return {"status": "ok", "retcode": 0, "data": {"feeds": feeds[:num], "has_more": False}}


def upload_image(img_bytes):
    ctx = get_ctx()
    data = {
        "filename": "filename",
        "uploadtype": "1",
        "albumtype": "7",
        "skey": ctx["skey"],
        "uin": str(ctx["uin"]),
        "p_skey": ctx["p_skey"],
        "output_type": "json",
        "base64": "1",
        "picfile": __import__("base64").b64encode(img_bytes).decode(),
    }
    req = urllib.request.Request(
        "https://up.qzone.qq.com/cgi-bin/upload/cgi_upload_image",
        data=urllib.parse.urlencode(data).encode(),
        headers={
            "User-Agent": UA,
            "referer": "https://user.qzone.qq.com/%d" % ctx["uin"],
            "origin": "https://user.qzone.qq.com",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Cookie": "uin=o%d; skey=%s; p_skey=%s" % (ctx["uin"], ctx["skey"], ctx["p_skey"]),
        },
        method="POST",
    )
    with OPENER.open(req, timeout=60) as r:
        d = parse_jsonp(r.read().decode("utf-8", "replace"))
    if d.get("ret") != 0 and d.get("code") != 0:
        raise RuntimeError("上传失败: %s" % json.dumps(d, ensure_ascii=False)[:200])
    data_obj = d.get("data") or {}
    picbo = str(data_obj.get("url") or "").split("&bo=", 1)[-1]
    richval = ",{},{},{},{},{},{},,{},{}".format(
        data_obj.get("albumid"), data_obj.get("lloc"), data_obj.get("sloc"),
        data_obj.get("type"), data_obj.get("height"), data_obj.get("width"),
        data_obj.get("height"), data_obj.get("width"),
    )
    return picbo, richval


def decode_image_input(item):
    if isinstance(item, bytes):
        return item
    if not isinstance(item, str):
        return None
    if item.startswith("data:"):
        m = re.match(r"data:image/[^;]+;base64,(.+)", item, re.S)
        if m:
            import base64
            return base64.b64decode(m.group(1))
    if item.startswith("base64://"):
        import base64
        return base64.b64decode(item[len("base64://"):])
    if item.startswith("http"):
        try:
            req = urllib.request.Request(item, headers={"User-Agent": UA})
            with OPENER.open(req, timeout=30) as r:
                return r.read()
        except Exception:
            return None
    try:
        with open(item, "rb") as f:
            return f.read()
    except Exception:
        return None


def action_publish(params):
    ctx = get_ctx()
    content = str(params.get("content") or "")
    if not content:
        return {"status": "failed", "retcode": 400, "message": "content 不能为空"}
    try:
        images = params.get("images") or []
        post_data = {
            "syn_tweet_verson": "1", "paramstr": "1", "who": "1", "con": content,
            "feedversion": "1", "ver": "1", "ugc_right": "1", "to_sign": "0",
            "hostuin": ctx["uin"], "code_version": "1", "format": "json",
            "qzreferrer": "https://user.qzone.qq.com/%d" % ctx["uin"],
        }
        if isinstance(images, list) and images:
            pic_bos, richvals = [], []
            for item in images[:9]:
                img = decode_image_input(item)
                if not img:
                    continue
                try:
                    pb, rv = upload_image(img)
                    if pb:
                        pic_bos.append(pb)
                        richvals.append(rv)
                except Exception as e:
                    print("upload_err:", str(e)[:200], flush=True)
            if pic_bos:
                post_data["pic_bo"] = ",".join(pic_bos)
                post_data["richtype"] = "1"
                post_data["richval"] = "\t".join(richvals)
        d = http_post(PUBLISH_URL, {"g_tk": ctx["gtk"], "uin": ctx["uin"]}, post_data, ctx)
        tid = (d.get("data") or {}).get("tid") or d.get("tid") or ""
        return {"status": "ok", "retcode": 0, "data": {"tid": tid}}
    except Exception as e:
        return {"status": "failed", "retcode": 500, "message": str(e)[:200]}


def action_delete(params):
    ctx = get_ctx()
    tid = str(params.get("tid") or "")
    try:
        d = http_post(DELETE_URL, {"g_tk": ctx["gtk"]}, {
            "uin": ctx["uin"], "topicId": "%d_%s__1" % (ctx["uin"], tid),
            "feedsType": 0, "feedsFlag": 0, "feedsKey": tid, "feedsAppid": 311,
            "feedsTime": int(time.time()), "fupdate": 1, "ref": "feeds",
        }, ctx)
        return {"status": "ok" if d.get("code") == 0 else "failed", "retcode": 0 if d.get("code") == 0 else 200,
                "message": "" if d.get("code") == 0 else "code=%s" % d.get("code")}
    except Exception as e:
        return {"status": "failed", "retcode": 500, "message": str(e)[:200]}


def action_like(params):
    ctx = get_ctx()
    tid = str(params.get("tid") or "")
    host = str(params.get("target_uin") or params.get("uin") or ctx["uin"])
    try:
        d = http_post(LIKE_URL, {"g_tk": ctx["gtk"]}, {
            "qzreferrer": "https://user.qzone.qq.com/%d" % ctx["uin"],
            "opuin": ctx["uin"], "unikey": "https://user.qzone.qq.com/%s/mood/%s" % (host, tid),
            "curkey": "https://user.qzone.qq.com/%s/mood/%s" % (host, tid),
            "appid": 311, "from": 1, "typeid": 0, "abstime": int(time.time()),
            "fid": tid, "active": 0, "format": "json", "fupdate": 1,
        }, ctx)
        return {"status": "ok" if d.get("code") == 0 else "failed", "retcode": 0}
    except Exception as e:
        return {"status": "failed", "retcode": 500, "message": str(e)[:200]}


# ---------------- 自动回复评论（桥接内部调用 LLM） ----------------
def _llm_cfg():
    prov = r"<AiQQ>\Cortico\deployments\providers\miaomiao"
    key = ""
    try:
        for line in open(prov + r"\.env", encoding="utf-8-sig"):
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                key = line.split("=", 1)[1].strip()
    except Exception:
        pass
    base = "https://api.deepseek.com"
    model = "deepseek-flash"
    try:
        pc = json.load(open(prov + r"\config.json", encoding="utf-8-sig"))
        base = str(pc.get("baseUrl") or base).rstrip("/")
        model = str((pc.get("spec") or {}).get("model") or model)
    except Exception:
        pass
    return base, key, model


def get_owner():
    try:
        cfg = json.load(open(r"<AiQQ>\Cortico\deployments\mybot\config.json", encoding="utf-8"))
        return str((cfg.get("worlds") or {}).get("qqbot", {}).get("owner") or "")
    except Exception:
        return ""


def llm_reply(prompt, is_owner=False):
    base, key, model = _llm_cfg()
    if not key:
        print("llm_reply: no key", flush=True)
        return ""
    # 空间评论是公开可见的：不露骨、不提性、不写QQ号。
    if is_owner:
        sys_prompt = "你是miaomiao，温柔软糯的精灵女仆。这是你QQ空间（公开可见）的评论，评论者是主人。用 1-2 句话回复：亲昵但克制，可以带一个颜文字；绝不说性暗示或露骨内容；不要写对方的QQ号，用「主人」或「你」称呼；不要提自己是AI。"
    else:
        sys_prompt = "你是miaomiao，温柔软糯的精灵女仆。这是你QQ空间（公开可见）的评论，评论者是普通访客。用 1 句话回复：礼貌友善、保持距离；不撒娇、不露骨、不提性；不写对方的QQ号，用昵称或「你」；可以带一个颜文字，不要暴露主人隐私，不要提自己是AI。"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 800,
        "effort": "high",
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with OPENER.open(req, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        return (d["choices"][0]["message"].get("content") or "").strip()
    except Exception as e:
        print("llm_reply err:", str(e)[:150], flush=True)
        return ""


def action_auto_reply(params):
    tid = str(params.get("tid") or "")
    host = str(params.get("target_uin") or "")
    cid = str(params.get("comment_id") or "")
    cname = str(params.get("comment_name") or "")
    ctext = str(params.get("comment_content") or "")
    if not tid or not cid:
        return {"status": "failed", "retcode": 400, "message": "缺少 tid/comment_id"}
    cuin = str(params.get("comment_uin") or "")
    is_owner = bool(cuin) and cuin == get_owner()
    # 先读该条说说的正文：回复要贴合动态内容，避免前言不搭后语。
    post_text = ""
    try:
        detail = action_detail({"tid": tid, "target_uin": host})
        if detail.get("status") == "ok":
            post_text = str((detail.get("data") or {}).get("content") or "").strip()
    except Exception as e:
        print("auto_reply detail err:", str(e)[:120], flush=True)
    post_line = ("你这条动态的正文是：「%s」。" % post_text[:300]) if post_text else "（没能读到动态正文，就只根据评论回应）"
    parent_text = str(params.get("parent_content") or "").strip()
    parent_line = ("这是在回复评论「%s」下面的楼中楼。" % parent_text[:120]) if parent_text else ""
    prompt = "有人在你（miaomiao）的空间动态下评论了。%s%s回复要贴合动态内容和上下文，别答非所问。这里是公开空间：不要说露骨或性相关的话，不要写任何QQ号。评论者：%s。评论内容：「%s」。请回复 ta。" % (post_line, parent_line, cname, ctext)
    text = llm_reply(prompt, is_owner)
    if not text:
        return {"status": "failed", "retcode": 500, "message": "LLM 生成失败"}
    text = text[:120]
    r = action_reply({"tid": tid, "target_uin": host, "comment_id": cid, "content": text})
    if r.get("status") == "ok":
        r["data"] = r.get("data") or {}
        r["data"]["text"] = text
    return r

ACTIONS = {
    "get_qzone_msg_detail": action_detail,
    "comment_qzone": action_comment,
    "auto_reply_comment": action_auto_reply,
    "reply_qzone_comment": action_reply,
    "get_qzone_feeds": action_feeds,
    "send_qzone_msg": action_publish,
    "delete_qzone_msg": action_delete,
    "like_qzone": action_like,
    "get_own_posts": lambda p: {"status": "ok", "retcode": 0, "data": {"posts": [
        {"tid": str(x.get("tid")), "content": x.get("content"), "comment_num": len(x.get("commentlist") or [])}
        for x in own_posts(int(p.get("num") or 5))]}},
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8", "replace"))
            action = body.get("action") or ""
            params = body.get("params") or {}
            fn = ACTIONS.get(action)
            result = fn(params) if fn else {"status": "failed", "retcode": 404, "message": "unsupported action: " + action}
        except Exception as e:
            result = {"status": "failed", "retcode": 500, "message": str(e)[:300]}
        out = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        out = json.dumps({"status": "ok", "retcode": 0, "data": {"uin": get_ctx()["uin"]}}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("qzone web bridge on %s:%d" % (HOST, PORT), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
