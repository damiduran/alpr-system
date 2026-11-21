#!/usr/bin/env python3
"""
Evergrand Cross-Platform UI/UX Playwright Audit Tool
Audits Desktop (1440x900), iPhone (390x844), and Android (360x800) viewports for:
- Zero horizontal overflow
- Login / primary CTA visibility & card containment
- iOS auto-zoom prevention (input font-size >= 16px on mobile)
- PWA manifest presence & validity
- Screenshot capture for empirical inspection
"""

import argparse
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

VIEWPORTS = [
    {"name": "desktop", "width": 1440, "height": 900, "is_mobile": False},
    {"name": "iphone", "width": 390, "height": 844, "is_mobile": True},
    {"name": "android", "width": 360, "height": 800, "is_mobile": True},
]


def parse_cookies(cookie_args, base_url):
    cookies = []
    for raw in cookie_args or []:
        if "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        cookies.append({"name": k.strip(), "value": v.strip(), "url": base_url})
    return cookies


def audit_url(url: str, name: str, out_dir: Path, cookies=None, check_pwa=True):
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"name": name, "url": url, "viewports": {}, "pwa": {}, "passed": True}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for vp in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                is_mobile=vp["is_mobile"],
                has_touch=vp["is_mobile"],
            )
            if cookies:
                context.add_cookies(cookies)

            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(700)

            metrics = page.evaluate(
                """(isMobile) => {
                    const docEl = document.documentElement;
                    const body = document.body;
                    const innerW = window.innerWidth;
                    const innerH = window.innerHeight;
                    const scrollW = Math.max(docEl.scrollWidth, body ? body.scrollWidth : 0);

                    // Check visible inputs font-size on mobile
                    const smallInputs = [];
                    if (isMobile) {
                        const inputs = document.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]):not([type="hidden"]), select, textarea');
                        for (const el of inputs) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width === 0 || rect.height === 0) continue;
                            const style = window.getComputedStyle(el);
                            if (style.display === 'none' || style.visibility === 'hidden') continue;
                            const fs = parseFloat(style.fontSize || '0');
                            if (fs > 0 && fs < 15.9) {
                                smallInputs.push({
                                    id: el.id || el.className || el.tagName,
                                    fontSize: fs
                                });
                            }
                        }
                    }

                    // Check login button container bounds if present
                    let loginBtnCheck = null;
                    const gBtn = document.getElementById('google-signin-btn');
                    if (gBtn) {
                        const rect = gBtn.getBoundingClientRect();
                        const style = window.getComputedStyle(gBtn);
                        if (style.display !== 'none' && rect.width > 0) {
                            loginBtnCheck = {
                                left: Math.round(rect.left),
                                right: Math.round(rect.right),
                                top: Math.round(rect.top),
                                bottom: Math.round(rect.bottom),
                                width: Math.round(rect.width),
                                fitsHorizontally: rect.left >= -1 && rect.right <= innerW + 1,
                                visibleWithoutScroll: rect.bottom <= innerH + 2
                            };
                        }
                    }

                    // Check PWA meta tags
                    const manifestEl = document.querySelector('link[rel="manifest"]');
                    const themeEl = document.querySelector('meta[name="theme-color"]');
                    const appleTouchEl = document.querySelector('link[rel="apple-touch-icon"]');

                    return {
                        innerWidth: innerW,
                        innerHeight: innerH,
                        scrollWidth: scrollW,
                        horizontalOverflowPx: Math.max(0, scrollW - innerW),
                        smallInputs,
                        loginBtnCheck,
                        manifestHref: manifestEl ? manifestEl.getAttribute('href') : null,
                        themeColor: themeEl ? themeEl.getAttribute('content') : null,
                        appleTouchIcon: appleTouchEl ? appleTouchEl.getAttribute('href') : null,
                    };
                }""",
                vp["is_mobile"],
            )

            screenshot_path = out_dir / f"{name}_{vp['name']}.png"
            page.screenshot(path=str(screenshot_path), full_page=False)

            issues = []
            if metrics["horizontalOverflowPx"] > 1:
                issues.append(f"Horizontal overflow: {metrics['horizontalOverflowPx']}px")
            if vp["is_mobile"] and metrics["smallInputs"]:
                issues.append(f"Inputs < 16px font (iOS zoom risk): {metrics['smallInputs']}")
            if metrics["loginBtnCheck"]:
                if not metrics["loginBtnCheck"]["fitsHorizontally"]:
                    issues.append(f"Login button overflows horizontally: {metrics['loginBtnCheck']}")
                if not metrics["loginBtnCheck"]["visibleWithoutScroll"]:
                    issues.append(f"Login button clipped below fold: {metrics['loginBtnCheck']}")

            if vp["name"] == "desktop" and check_pwa:
                manifest_href = metrics.get("manifestHref")
                pwa_ok = bool(manifest_href and metrics.get("themeColor") and metrics.get("appleTouchIcon"))
                manifest_status = None
                if manifest_href:
                    from urllib.parse import urljoin
                    m_url = urljoin(url, manifest_href)
                    resp = page.request.get(m_url)
                    manifest_status = resp.status
                    if resp.status != 200:
                        pwa_ok = False
                        issues.append(f"Manifest returned HTTP {resp.status}: {m_url}")
                else:
                    issues.append("Missing <link rel='manifest'>")
                report["pwa"] = {
                    "manifestHref": manifest_href,
                    "manifestStatus": manifest_status,
                    "themeColor": metrics.get("themeColor"),
                    "appleTouchIcon": metrics.get("appleTouchIcon"),
                    "ok": pwa_ok,
                }

            vp_passed = len(issues) == 0
            if not vp_passed:
                report["passed"] = False

            report["viewports"][vp["name"]] = {
                "passed": vp_passed,
                "issues": issues,
                "metrics": metrics,
                "screenshot": str(screenshot_path),
            }
            context.close()

        browser.close()

    return report


def main():
    parser = argparse.ArgumentParser(description="Evergrand Cross-Platform UI/UX Playwright Audit")
    parser.add_argument("--url", required=True, help="Target page URL")
    parser.add_argument("--name", required=True, help="Label for output screenshots & report")
    parser.add_argument("--out-dir", default="/tmp/evergrand_ux_audit", help="Output directory")
    parser.add_argument("--cookie", action="append", help="Optional cookie(s) as name=value")
    parser.add_argument("--skip-pwa", action="store_true", help="Skip PWA manifest check")
    args = parser.parse_args()

    cookies = parse_cookies(args.cookie, args.url)
    report = audit_url(args.url, args.name, Path(args.out_dir), cookies=cookies, check_pwa=not args.skip_pwa)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
