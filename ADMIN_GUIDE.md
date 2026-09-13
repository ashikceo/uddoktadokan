# Admin Panel — Admin Use Guide

This guide explains how to manage **every part of the website** from the admin panel
(`http://YOUR-DOMAIN/admin/` — login with a superuser account).

Everything below is organized exactly like the menu on the left side of the admin.

---

## 1. Homepage control (most important section)

**Menu: `Homepage & Page Settings` → `Homepage & Page Settings`**

This is a single page that turns every homepage section **ON / OFF**, renames
headings, changes buttons and the video. There is exactly one row — you can only
edit it (no add / delete needed).

| Section in the form | What it controls | Default |
|---|---|---|
| B2B / B2C Buttons | the two buttons below the top slider; change text, icon and link / hide them | ON |
| All Over Available Product (tabs) | the first product block + its 4 tab names (All / New / Discounted / Hot) | ON |
| Random Product List (sidebars) | the scrolling "Random Product List" boxes on the right side | ON |
| Partner Product Sections | "All Partner Product" and "All Partner Hot Products" blocks | ON |
| Blog Marquee + Video | the "New Arrival Product" marquee (blog posts) and the "Our Videos" YouTube box — paste any YouTube **embed** URL | ON |
| Promo Cards + Brand Marquee | show/hide the 4 promo cards and the brands strip; the heading text | ON |
| Home Banner Strip | when ON, the images under **Home Banner** appear as a wide strip above the promo cards | OFF |
| Shop Grid Page | the shop page title ("ALL PRODUCTS") and the "Labels" filter list captions | ON |
| Product Detail Page | social share buttons + the Delivery / Return / Payment texts | ON |
| Other Page Titles | "Contact Us" and "Discount Card" page titles | — |

> Save with the **Save** button at the bottom. Changes appear immediately.

---

## 2. Promo Cards
**Menu: `Promo Cards`**

The 4 cards with icons ("Buy 2 items", "Daily Sales", …) are rows here. You can:
- **Add** a new card (green `+ Add` button)
- **Edit** title, subtitle, Font Awesome icon name (e.g. `fa fa-gift`), and an optional **link**
- **Order** them by typing numbers in the `Order` column
- **Hide / Show** by ticking/un-ticking `is_active` on the list, or **Delete** the row

> Note: the colour of the first 4 cards uses a fixed colour palette (red / orange /
> green / blue). A 5th card will look plain gray until you customise it in CSS.

---

## 3. Brand Logos
**Menu: `Brand Logos`**

The "Our Partner Brands" marquee. Add / edit / hide / delete / reorder brand logo
images exactly like promo cards. Links are optional. The marquee scrolls
automatically and all rows are duplicated automatically, so a single momentum is
enough.

---

## 4. Header / Mobile Menu
**Menu: `Nav Menu`**

A row per menu item. A **link** is either a Named URL (e.g. `home`, `shop_grid`,
`partner_list`, `union_list`, `dealer_list`, `seller_list`, `discount_card`,
`blog_list`) or a direct Path (e.g. `/shop_grid/`).

Each row has:
- `Show in desktop menu` — appears in the big top menu
- `Show in mobile menu` — appears in the mobile menu
- `is_active` — master switch
- `order` — position
- `login_required` / `logout_required` — only show for logged-in / logged-out users

Example: set `Blog` row to `Show in desktop menu` will add a Blog link to the big
menu too.

---

## 5. Banners & Sliders (every image slider)

| Menu section | Where it appears | Scope |
|---|---|---|
| `Slider` | the big top slider on the **home page** (if empty, two default images show) | home |
| `Home Banner` | the wide banner strip — appears on the home page only when **Homepage & Page Settings → show_home_banner** is ON | home |
| `Shop Banner` | the top slider on the **Shop Grid** page — set its timing/size in `Shop Slider Settings` | shop |
| `Shop Sidebar Slider` | small vertical slider in the right column; choose `section` = home_all / home_partner / home_hot / shop / partnership | home + shop + partner |
| `Shop Sidebar Bottom Banner` | static small banners in the right column; same section choices | home + shop + partner |
| `Side Banner` | sidebar banners; `partner = (empty)` = main site, otherwise a partner store | site + partner |

Every one of these supports: add, edit, hide (`is_active`), order, delete. Upload
your image, optionally set a **link URL** (clicking the banner goes there) and a
**title** (shown as a caption overlay where supported).

---

## 6. Products, Categories, Partners, Blog
- **Categories** — top-level + sub-categories (children). Counts are automatic.
- **Products** — full control: name, price, images, colors/sizes variants, label
  (`new` / `hot` / `discounted`), stock, `Available` / `Published` switches. Product
  images, colour and size variants are edited inside each product.
- **Partners** → add/edit partner stores. Partner **sliders, banners, nav menus**
  are edited inside the partner record. Each partner has `Show Products on Website`
  and section switch toggles.
- **Blog Posts** — shown in the home marquee ("New Arrival Product") and the Blog
  page; add/edit/delete posts.
- **Landing Page** — full marketing pages (hero, about, stats, CTA, colours). If you
  do not use landing pages you can hide them by setting `is_active` off.

---

## 7. Site-wide settings
**Menu: `Site Settings`**

Logo, favicon, site name/tagline, **search placeholder**, phone, WhatsApp,
addresses, footer columns. On/off switches at the bottom:
- Show newsletter section
- Show contact info column
- Show follow-us (social) column
- Show policy buttons (Terms / Return & Refund / Company Policy)
- Show copyright bottom bar
- Show payment card icons

**Menu: `Pages`** — the Terms & Conditions, Return & Refund and Company Policy
pages (edit the content with the built-in rich text editor). `show_in_footer`
controls whether a page gets a policy button. You can also **add new pages** and
tick `show_in_header` / `show_in_footer`.

**Menu: `Social Media Links`** — footer icons **and** the left floating bar
(colour + icon + link, ordered).

**Menu: `Payment Icons`** — the small payment brand images in the footer.

**Menu: `News Ticker`** — the scrolling notification line at the top; also the
search-placeholder text type.

---

## 8. Shipping, fees, coupons, wallet
- `Server Fee` — the fee (fixed/percentage) shown at checkout; each can have an info link.
- `Coupon` — discount codes; manage usages.
- `Shipping Rule` — delivery charges & free-shipping thresholds.
- `Payout Method` / `Wallet → Wallet Settings` — partner wallet behaviour.
- `Wallet Recharge Instruction` — bank/mobile-banking instructions shown to users.

---

## 9. Products from partners (POS / Orders)
Orders and POS orders can be viewed/printed/exported from `Orders` and
`POS Order` / `Medicine POS Order` admin pages. Delivery logs live inside an order.
Custom Orders are approved/rejected in `Custom Orders`. `Medicine Products` feed
the medicine POS catalog; subscriptions and packages are managed under
`Medicine Subscription` / `Subscription Package`.

---

## 10. Common rules for every section
- **Show / hide** any row with its `is_active` checkbox (tick = show, untick = hide).
- **Ordering**: type numbers in the `order` column and press **Save** — lower numbers first.
- **Editing**: click the row title → change → **Save**.
- **Adding**: green **+ Add** button on a list page.
- **Deleting**: select a row with the check-box, choose "Delete selected", press Go.

Everything saves instantly — refresh the website to see changes. For the homepage
and most banners no page refresh cache is needed; if you run a browser cache,
hard-refresh with **Ctrl+F5**.