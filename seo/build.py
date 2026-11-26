#!/usr/bin/env python3
"""Dựng trang SEO tĩnh "thành phố × bữa ăn" cho homnayangi.xyz từ data.json.

Chạy lại mỗi khi data.json đổi:  python3 seo/build.py
Sinh ra: /<thanh-pho>/index.html, /<thanh-pho>/<bua>/index.html, sitemap.xml, robots.txt
Chỉ làm trang cho thành phố đã có quán (tránh trang rỗng, mỏng nội dung).
"""
import json, html, os, unicodedata, datetime, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://homnayangi.xyz"
MIN_PARTNERS = 10  # thành phố có ít hơn số quán này thì chưa làm trang

MEALS = [
    # key, slug, tiêu đề ngắn, câu hỏi, giờ, mô tả khoảnh khắc
    ("sang", "sang-nay-an-gi", "Ăn sáng", "Sáng nay ăn gì", "6:00–9:30",
     "Sáng ra vội đi làm, đi học mà đứng trước cửa vẫn chưa nghĩ ra ăn gì."),
    ("trua", "trua-nay-an-gi", "Ăn trưa", "Trưa nay ăn gì", "10:30–13:00",
     "11 giờ, cả phòng nhìn nhau hỏi câu quen thuộc mà không ai chịu trả lời."),
    ("toi", "toi-nay-an-gi", "Ăn tối", "Tối nay ăn gì", "17:00–20:00",
     "Tan làm mệt, không muốn nấu, mở app đặt món lướt mãi vẫn chưa chọn được."),
    ("khuya", "an-dem", "Ăn đêm", "Đêm nay ăn gì", "22:00–2:00",
     "Gần nửa đêm, bụng réo, cần món nóng hoặc món nhâm nhi mà quán vẫn còn giao."),
    ("vat", "an-vat", "Ăn vặt", "Ăn vặt gì", "14:00–17:00",
     "Giữa chiều buồn miệng, muốn gì đó lai rai cho qua cơn thèm."),
    ("uong", "uong-gi", "Đồ uống", "Hôm nay uống gì", "cả ngày",
     "Cần ly gì đó cho tỉnh táo hoặc giải nhiệt mà menu dài quá chọn không nổi."),
    ("nhau", "nhau-gi", "Món nhậu", "Nhậu gì hôm nay", "18:00–23:00",
     "Hội bạn đã chốt kèo, chỉ còn mỗi việc chọn món đưa cay."),
]

def norm(t):
    return unicodedata.normalize("NFC", t.lower()).replace("mỳ", "mì")

def e(t):
    return html.escape(str(t), quote=True)

def vis(xs):
    return [x for x in xs if not x.get("hidden")]

def money(k):  # giá trong dishes là nghìn đồng
    return f"{k}k"

CSS = """:root{--bg:#fff8f1;--card:#fff;--ink:#1e1b18;--mute:#7a6f66;--pri:#ff5a36;--line:#f0e3d6}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.55}
.wrap{max-width:720px;margin:0 auto;padding:16px}a{color:var(--pri)}
nav.crumb{font-size:13px;color:var(--mute)}nav.crumb a{color:var(--mute)}
h1{font-size:26px;line-height:1.25;margin:8px 0}h2{font-size:20px;margin:28px 0 10px}
.lead{color:var(--mute);margin:0 0 16px}
.cta{display:block;text-align:center;background:var(--pri);color:#fff;text-decoration:none;font-weight:700;font-size:18px;padding:16px;border-radius:16px;margin:16px 0}
.cta small{display:block;font-weight:400;font-size:13px;opacity:.9}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;margin:10px 0}
#que{text-align:center}#que b{display:block;font-size:22px;margin:6px 0}#que button{font:inherit;border:0;background:var(--ink);color:#fff;border-radius:999px;padding:10px 18px;font-weight:600;cursor:pointer}
ul.dish{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:1fr 1fr;gap:8px}
ul.dish li{background:#fff;border:1px solid var(--line);border-radius:12px;padding:8px 10px;font-size:15px}ul.dish span{color:var(--mute);font-size:13px}
.shop{display:flex;gap:12px;align-items:center}.shop img{width:96px;height:60px;object-fit:cover;border-radius:10px;flex:none;background:#eee}
.shop h3{font-size:16px;margin:0}.shop p{margin:2px 0;font-size:13px;color:var(--mute)}
.btn{display:inline-block;margin-top:4px;font-size:14px;font-weight:600;text-decoration:none}
.links{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none}.links a{display:inline-block;background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;text-decoration:none;color:var(--ink);font-size:14px}
footer{color:var(--mute);font-size:13px;margin:32px 0 16px}
@media(max-width:420px){ul.dish{grid-template-columns:1fr}.shop img{width:72px;height:48px}}"""

def page(title, desc, path, body, jsonld):
    url = SITE + path
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{SITE}/web.png">
<meta property="og:locale" content="vi_VN">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#ff5a36">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍜</text></svg>">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body><div class="wrap">
{body}
<footer>Hôm nay ăn gì? · <a href="/">homnayangi.xyz</a> · Một sản phẩm của AL Group. Một số liên kết quán là liên kết tiếp thị liên kết, bạn đặt món giá vẫn như bình thường.</footer>
</div></body></html>
"""

def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u}
                                for i, (n, u) in enumerate(items)]}

def shop_card(p, dish_hint=None):
    link = p["links"][0]
    img = f'<img src="{e(p["cover"])}" alt="{e(p["name"])}" loading="lazy" width="96" height="60">' if p.get("cover") else ""
    addr = p.get("address") or p.get("area") or ""
    tags = ", ".join(p.get("tags", [])[:5])
    return (f'<div class="card shop">{img}<div><h3>{e(p["name"])}</h3>'
            f'<p>{e(addr)}</p><p>Có: {e(tags)}</p>'
            f'<a class="btn" href="{e(link)}" rel="sponsored nofollow noopener" target="_blank">Xem menu & đặt trên ShopeeFood →</a></div></div>')

def build():
    d = json.load(open(os.path.join(ROOT, "data.json"), encoding="utf-8"))
    partners = [p for p in vis(d["partners"]) if p.get("links")]
    today = datetime.date.today().isoformat()
    urls = [("/", "1.0")]
    made = []
    for c in d["cities"]:
        cp = [p for p in partners if (p.get("cityId") or "ha-noi") == c["id"]]
        if len(cp) < MIN_PARTNERS:
            continue
        city, cid = c["name"], c["id"]
        meal_links = []
        for key, slug, short, q, hours, moment in MEALS:
            dishes = vis(d["dishes"].get(key, []))
            rows, used, matched = [], set(), []
            for dsh in dishes:
                n = norm(dsh["name"])
                ps = [p for p in cp if any(norm(t) in n for t in p.get("tags", []))]
                matched.append((dsh, ps))
                for p in ps:
                    if p["id"] not in used:
                        used.add(p["id"]); rows.append((dsh["name"], p))
            if not rows:
                continue
            path = f"/{cid}/{slug}/"
            app = f"/?city={cid}&meal={key}&ref=seo"
            title = f"{q} ở {city}? Xóc quẻ chọn món + {len(rows)} quán giao tận nơi"
            desc = (f"{q} ở {city}: {len(dishes)} món hợp giờ {hours.lower()} như "
                    f"{', '.join(x['name'] for x in dishes[:4])}… kèm {len(rows)} quán {city} đặt được trên ShopeeFood. "
                    f"Lưỡng lự thì xóc một quẻ cho trời chọn.")
            dish_li = "".join(f'<li>{e(x["name"])} <span>· khoảng {money(x["price"])}' +
                              (f' · {len(ps)} quán' if ps else "") + "</span></li>" for x, ps in matched)
            shops = "".join(shop_card(p) for _, p in rows[:24])
            pool = json.dumps([[x["name"], [p["links"][0] for p in ps][:3], [p["name"] for p in ps][:3]]
                               for x, ps in matched], ensure_ascii=False)
            other = "".join(f'<li><a href="/{cid}/{s2}/">{e(q2)} ở {e(city)}</a></li>'
                            for k2, s2, _, q2, *_ in MEALS if k2 != key)
            body = f"""<nav class="crumb"><a href="/">Hôm nay ăn gì</a> › <a href="/{cid}/">{e(city)}</a> › {e(short)}</nav>
<h1>{e(q)} ở {e(city)}?</h1>
<p class="lead">{e(moment)} Trang này gom sẵn {len(dishes)} món hợp khung {e(hours)} và {len(rows)} quán ở {e(city)} đang giao trên ShopeeFood. Không chọn nổi thì để trời quyết.</p>
<div class="card" id="que"><div>🎋 Xóc nhanh một quẻ {e(short.lower())}</div><b id="qmon">?</b><div id="qshop" style="font-size:14px;color:var(--mute)"></div><p><button id="qbtn" type="button">Xóc quẻ</button></p></div>
<a class="cta" href="{e(app)}">🎲 Mở bản đầy đủ: xóc quẻ, ném xúc xắc, quay xem ai trả tiền<small>{e(city)} · {e(short)} · miễn phí, không cần cài app</small></a>
<h2>{len(dishes)} món {e(short.lower())} hay được chọn</h2>
<ul class="dish">{dish_li}</ul>
<h2>Quán {e(short.lower())} ở {e(city)} giao tận nơi</h2>
{shops}
<h2>Mẹo chọn món nhanh</h2>
<p>Đi nhóm đông thì để mỗi người xóc một quẻ, món nào ra hai lần là chốt. Muốn công bằng chuyện trả tiền thì dùng nút "quay xem ai trả tiền" trong <a href="{e(app)}">bản đầy đủ</a>. Món giá ở trên là mức tham khảo một suất, giá thật xem trong menu từng quán.</p>
<h2>Bữa khác ở {e(city)}</h2>
<ul class="links">{other}</ul>
<script>(function(){{var P={pool},b=document.getElementById("qbtn"),m=document.getElementById("qmon"),s=document.getElementById("qshop");b.onclick=function(){{var x=P[Math.floor(Math.random()*P.length)];m.textContent=x[0];s.innerHTML="";if(x[1].length){{s.append("Gần đây có: ");x[1].forEach(function(u,i){{var a=document.createElement("a");a.href=u;a.rel="sponsored nofollow noopener";a.target="_blank";a.textContent=x[2][i];s.append(a);if(i<x[1].length-1)s.append(", ")}})}}else s.textContent="Món này mở bản đầy đủ để xem thêm quán.";b.textContent="Xóc lại"}}}})();</script>"""
            ld = [crumbs([("Hôm nay ăn gì", "/"), (city, f"/{cid}/"), (short, path)]),
                  {"@context": "https://schema.org", "@type": "ItemList", "name": f"Quán {short.lower()} ở {city}",
                   "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                        "item": {"@type": "Restaurant", "name": p["name"],
                                                 **({"address": p["address"]} if p.get("address") else {}),
                                                 **({"image": p["cover"]} if p.get("cover") else {})}}
                                       for i, (_, p) in enumerate(rows[:24])]}]
            out = os.path.join(ROOT, cid, slug)
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(page(title, desc, path, body, ld))
            urls.append((path, "0.8")); made.append(path)
            meal_links.append((slug, q, short, len(dishes), len(rows)))
        # trang thành phố
        path = f"/{cid}/"
        title = f"Hôm nay ăn gì ở {city}? Chọn món sáng, trưa, tối, đêm + {len(cp)} quán giao tận nơi"
        desc = f"Bí món ở {city}? Chọn theo bữa: sáng, trưa, tối, ăn đêm, ăn vặt, đồ uống, nhậu. {len(cp)} quán {city} trên ShopeeFood và nút xóc quẻ để trời chọn."
        li = "".join(f'<div class="card"><h3 style="margin:0"><a href="/{cid}/{s}/">{e(q)} ở {e(city)}?</a></h3><p style="margin:4px 0 0;color:var(--mute)">{n1} món · {n2} quán</p></div>'
                     for s, q, _, n1, n2 in meal_links)
        body = f"""<nav class="crumb"><a href="/">Hôm nay ăn gì</a> › {e(city)}</nav>
<h1>Hôm nay ăn gì ở {e(city)}?</h1>
<p class="lead">Chọn bữa bên dưới để xem món hợp giờ và quán ở {e(city)} đang giao. Hoặc mở thẳng trò xóc quẻ để trời chọn giúp.</p>
<a class="cta" href="/?city={cid}&amp;ref=seo">🎲 Xóc quẻ chọn món ở {e(city)}<small>miễn phí, không cần cài app</small></a>
{li}"""
        open(os.path.join(ROOT, cid, "index.html"), "w", encoding="utf-8").write(
            page(title, desc, path, body, crumbs([("Hôm nay ăn gì", "/"), (city, path)])))
        urls.insert(1, (path, "0.9")); made.append(path)
    # cập nhật dòng liên kết thành phố ở cuối trang chủ
    city_links = " · ".join(f'<a href="/{c["id"]}/">{c["name"]}</a>' for c in d["cities"]
                            if os.path.exists(os.path.join(ROOT, c["id"], "index.html")) and f"/{c['id']}/" in made)
    ip = os.path.join(ROOT, "index.html"); ih = open(ip, encoding="utf-8").read()
    ih2 = re.sub(r'<p class="foot">Chọn món theo thành phố:.*?</p>', f'<p class="foot">Chọn món theo thành phố: {city_links}</p>', ih)
    if ih2 != ih: open(ip, "w", encoding="utf-8").write(ih2)
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
         "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod><priority>{pr}</priority></url>\n" for u, pr in urls) + "</urlset>\n"
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(sm)
    open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: {SITE}/sitemap.xml\n")
    print(len(made), "trang:"); print("\n".join(made))

if __name__ == "__main__":
    build()
