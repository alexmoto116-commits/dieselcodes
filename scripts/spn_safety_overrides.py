"""Apply the four reviewed DieselCodes diagnostic corrections after HTML generation."""
import argparse
from html import escape
import json
from pathlib import Path
import re

STOP = "If a red STOP ENGINE warning is on, pull off safely, shut down as directed by the vehicle manual and obtain service."
CONDITIONAL = "The SPN alone does not establish whether the vehicle can continue. Follow the vehicle's warnings and manufacturer instructions."
TITLE_3226 = "SPN 3226 — Aftertreatment Outlet NOx Sensor"
DESC_3226 = "Interpret SPN 3226 by reporting controller and FMI. Distinguish outlet NOx sensor faults from an SCR conversion-efficiency fault."
DESC_110 = "Interpret SPN 110 by FMI, distinguish overheating from coolant sensor circuit faults, and check the vehicle manufacturer’s warning instructions."

PAGES = {
    3719: {
        "label": "Check warning and FMI", "hint": "Red STOP: stop safely and obtain service",
        "diagnosis": """
<p>SPN 3719 reports the estimated soot load of DPF 1. Confirm the reporting controller, FMI and warning lamps. Check the vehicle's current regeneration eligibility before considering a parked regeneration.</p>
<h3>Check order</h3><ol>
<li><b>Red STOP ENGINE:</b> """ + STOP + """ Do not initiate a driver-requested regeneration in response to a red STOP warning.</li>
<li><b>FMI 15 or 16:</b> Soot load is above the normal range in the applicable OEM procedure. On the 2010 MaxxForce example a flashing DPF lamp can call for parked regeneration. Use the instructions for the actual vehicle and only start the procedure when the vehicle permits it.</li>
<li><b>FMI 0:</b> Treat it as a high-severity soot or restriction report. Detroit GHG14 has a specific diagnostic path. Check companion faults and the OEM service procedure before attempting regeneration.</li>
<li>If the warning returns, record incomplete or inhibited regeneration and check pressure-sensing faults under the OEM procedure. Ash requires appropriate filter service.</li></ol>""",
        "drive": STOP + " For a DPF lamp without red STOP, use the manufacturer's warning stages and regeneration instructions.",
        "effect": "Soot accumulation can bring a derate or shutdown depending on the platform. A high-soot FMI alone gives no universal driving window or permission to regenerate.",
        "spot": "Record the FMI, warning lamps and whether regeneration is inhibited. If the vehicle calls for and permits a parked regeneration, use the prescribed location and clearance. In all other cases follow the applicable service procedure.",
        "sources": [("Navistar IK1200894 — MaxxForce warning lamps and STOP procedure","https://static.nhtsa.gov/odi/tsbs/2013/MC-10166334-9999.pdf"),
                    ("Detroit 2 12-14 — GHG14 SPN 3719 FMI 0 and 16","https://static.nhtsa.gov/odi/tsbs/2014/MC-10126756-9999.pdf")],
    },
    3226: {
        "label": "Check reporting module and FMI", "hint": "Follow the vehicle warnings",
        "diagnosis": """
<p>SPN 3226 concerns the downstream nitrogen oxides (NOx) reading or its sensor channel. The outlet signal is used to assess SCR conversion, but a problem with that signal does not establish that the catalyst has failed. <a href="/kody/spn-4364.html">SPN 4364</a> is the separate conversion-efficiency parameter.</p>
<h3>Check order</h3><ol>
<li>Record the source module, engine and FMI. Use the manufacturer's definition for that controller.</li>
<li>For a reported circuit, supply or communication fault, inspect the downstream sensor connector and harness. Follow OEM power and network tests before replacing parts.</li>
<li>For Detroit GHG17 heavy-duty, FMI 20 indicates downstream NOx sensor drift low and FMI 21 indicates drift high in the cited bulletin. Do not transfer those directions to a different implementation.</li>
<li>Use the OEM test conditions to evaluate live inlet and outlet readings. Check companion dosing or SCR efficiency faults under their own procedures.</li></ol>""",
        "drive": CONDITIONAL + " If the vehicle shows a red STOP warning or an active speed limitation that makes traffic unsafe, stop safely and seek service.",
        "effect": "A downstream signal fault can affect aftertreatment monitoring. Any warning, derate or inducement depends on the engine and companion faults. This code gives no universal countdown.",
        "spot": "Save the exact FMI and companion codes. If the exhaust has cooled and access is safe, look for obvious damage to the outlet sensor harness. A full DEF tank does not rule out a sensor, circuit or communication fault.",
        "sources": [("Detroit 06 09-17 — GHG17 SPN 3226 FMI 20 and 21","https://static.nhtsa.gov/odi/tsbs/2017/MC-10156386-9999.pdf"),
                    ("Detroit GHG14 — distinct SCR conversion-efficiency diagnosis","https://static.nhtsa.gov/odi/tsbs/2014/MC-10141901-9999.pdf")],
    },
    110: {
        "label": "Check temperature and FMI", "hint": "Red STOP or overheating: stop safely",
        "diagnosis": """
<p>SPN 110 is the engine coolant temperature parameter. First distinguish a reported high temperature from a sensor circuit fault. For example, Cummins Fault Code 145 (FMI 4) reports low circuit voltage. Confirm actual coolant temperature independently.</p>
<h3>Check order</h3><ol>
<li>With a red STOP warning, abnormal temperature or evidence of overheating, stop safely and follow the vehicle's shutdown procedure. Never open a hot pressurized cooling system.</li>
<li>For a temperature-high FMI on the applicable engine, inspect coolant level after cooling, then follow the OEM procedure for leaks, airflow, coolant circulation and fan operation.</li>
<li>For a circuit FMI, inspect the sensor connector and harness. Use the engine-specific wiring diagram and test limits. Compare cold-soaked readings with a reliable reference as the manufacturer directs.</li>
<li>For a below-normal temperature report, confirm the operating conditions and evaluate warm-up using the engine manual before replacing parts.</li></ol>""",
        "drive": "Stop safely for a red STOP warning or evidence of overheating and follow the vehicle manufacturer's instructions. An electrical FMI can make the temperature display unreliable. Verify temperature independently and consult the manufacturer before deciding to continue.",
        "effect": "Actual overheating can damage the engine. An electrical sensor fault can instead prevent reliable temperature monitoring, including on a cool engine. Verify which condition is present before selecting a repair.",
        "spot": "With the engine cool, check coolant level according to the manual and look for external leaks. Record the FMI and gauge behavior. Have the temperature and sensor circuit verified if the display cannot be trusted.",
        "sources": [("Cummins fault-code table — coolant temperature and circuit faults","https://mart.cummins.com/imagelibrary/data/assetfiles/0057257.pdf"),
                    ("Freightliner Cascadia Driver’s Manual — coolant warning and STOP Engine lamp","https://dtnacontent-dtna.prd.freightliner.com/content/dam/public/dtna-servicelit/dtna/pdfs/en_us/freightliner/drivers-manuals/Cascadia%20Driver%27s%20Manual_.pdf")],
    },
    4364: {
        "label": "Check warnings and companion codes", "hint": "Driving decision depends on vehicle instructions",
        "diagnosis": """
<p>SPN 4364 concerns SCR NOx conversion efficiency. Detroit GHG14 FMI 18 reports conversion below the expected level under the monitor's test conditions. An efficiency fault can also involve the DEF supply, dosing, exhaust or the NOx measurements used by the monitor.</p>
<h3>Check order</h3><ol>
<li>Identify the engine, emissions platform and FMI. Record companion codes before clearing anything.</li>
<li>Resolve the related aftertreatment faults in the OEM order. Vehicle-specific tests may cover DEF quality and dosing, exhaust leakage and both NOx signals.</li>
<li>Use the manufacturer’s conversion-efficiency test under the specified operating conditions. Confirm the result before replacing the catalyst or ordering a different sensor.</li>
<li>Verify repair using the applicable service routine and check the aftertreatment warning and inducement status.</li></ol>""",
        "drive": CONDITIONAL + " If a red STOP warning is active or a speed or power restriction makes continued travel unsafe, stop safely and obtain service.",
        "effect": "Aftertreatment warnings and torque or speed restrictions depend on the engine, calibration and active companion faults. This efficiency code does not establish when a restriction will occur.",
        "spot": "Record the exact FMI, dashboard messages and companion faults. Check the DEF level and last refill details. Use an OEM scan tool and service procedure to test dosing, fluid quality, exhaust integrity and the NOx readings.",
        "sources": [("Detroit GHG14 — SPN 4364 FMI 18 diagnostic sequence","https://static.nhtsa.gov/odi/tsbs/2014/MC-10141901-9999.pdf")],
    },
}

COOLANT_FAQ = [
    ("What does SPN 110 FMI 4 mean on the documented Cummins engine?",
     "Cummins Fault Code 145 reports low coolant temperature sensor circuit voltage. Actual coolant temperature requires independent confirmation."),
    ("When should I stop for a coolant warning?",
     "Stop safely if a red STOP warning or signs of overheating are present and follow the vehicle manual. Never open a hot pressurized cooling system."),
]


def sub_one(pattern, replacement, page):
    result, count = re.subn(pattern, replacement, page, flags=re.S)
    if count != 1:
        raise ValueError(f"Expected one HTML slot, got {count}: {pattern}")
    return result


def section(page, title, inner):
    return sub_one(r'(<section(?: [^>]*)?><h2[^>]*>'+re.escape(title)+r'</h2>).*?(</section>)',
                   lambda m:m[1]+inner+m[2], page)


def paragraph(value):
    return "<p>"+escape(value)+"</p>"


def apply_overrides(relative_path, page):
    hit = re.fullmatch(r"kody/spn-(\d+)\.html",relative_path.replace("\\","/"))
    if not hit or int(hit[1]) not in PAGES:
        return page
    spn = int(hit[1])
    data = PAGES[spn]
    page = sub_one(r'<p class="vline[^"]*">.*?</p>',
                   lambda _:f'<p class="vline t-warn"><b>{escape(data["label"])}</b>'
                            f'<span class="hz">{escape(data["hint"])}</span></p>',page)
    page = section(page,"How to check it yourself",data["diagnosis"])
    for title,key in (("Can I keep driving","drive"),("What happens if you keep driving","effect"),
                      ("What to check on the spot","spot")):
        page = section(page,title,paragraph(data[key]))
    if spn in (110,3719):
        page = section(page,"Which codes follow",
                       paragraph("Review protection or derate faults with the rest of the fault record. Confirm each active condition through the manufacturer’s diagnostic procedure."))
    if spn == 3719:
        page = page.replace("J1939 code SPN 3719. No factory wording for it in the reference — below is the standard meaning of FMI.",
                            "J1939 code SPN 3719. The vehicle manufacturer’s warning stages and regeneration conditions take priority.")
        page = page.replace("<h2>Common FMI values</h2>","<h2>J1939 FMI definitions</h2>")
    if spn == 110:
        page = section(page,"What SPN 110 and its FMI tell you",paragraph(
            "The parameter is engine coolant temperature. A high-temperature FMI and a circuit voltage FMI call for different diagnostic tests. Check the engine and reporting module before applying a definition."))
        page = page.replace("<h2>Causes of a real overheat, most common first</h2>","<h2>Possible causes of confirmed overheating</h2>")
        page = section(page,"Possible causes of confirmed overheating",paragraph(
            "Possible causes include loss of coolant, poor airflow, inadequate circulation or a thermostat fault. Use the engine-specific service procedure to isolate them."))
        page = section(page,"How to check",paragraph(data["spot"]))
        page = section(page,"Can you keep driving?",paragraph(data["drive"]))
        page = section(page,"Questions and answers","".join(
            f'<h3 class="faq-q">{escape(q)}</h3>{paragraph(a)}' for q,a in COOLANT_FAQ))
    if spn == 3226:
        page = page.replace("SPN 3226 — NOx at SCR outlet (catalyst efficiency)", TITLE_3226)
        page = page.replace("NOx at SCR outlet (catalyst efficiency)","Aftertreatment outlet NOx sensor")
    if spn in (110,3226):
        description = DESC_110 if spn == 110 else DESC_3226
        for attr in ('name="description"', 'property="og:description"'):
            page = sub_one(r'(<meta '+attr+r' content=")[^"]*',
                           lambda m:m[1]+escape(description,quote=True),page)
    def update_schema(match):
        obj = json.loads(match[1])
        if obj.get("@type") == "FAQPage":
            if spn != 110:
                return ""
            obj["mainEntity"] = [{"@type":"Question","name":q,
                                  "acceptedAnswer":{"@type":"Answer","text":a}} for q,a in COOLANT_FAQ]
        elif spn == 3226 and obj.get("@type") == "TechArticle":
            obj.update(headline=TITLE_3226,description=DESC_3226)
        elif spn == 110 and obj.get("@type") == "TechArticle":
            obj["description"] = DESC_110
        elif spn == 3226 and obj.get("@type") == "BreadcrumbList":
            obj["itemListElement"][-1]["name"] = TITLE_3226
        else:
            return match[0]
        return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False)+"</script>"
    page = re.sub(r'<script type="application/ld\+json">(.*?)</script>',update_schema,page,flags=re.S)
    sources = "".join(f'<li><a href="{escape(url,quote=True)}">{escape(label)}</a></li>'
                      for label,url in data["sources"])
    marker = '<section id="manufacturer-diagnostics">'
    block = marker+"<h2>Manufacturer references</h2><ul>"+sources+"</ul></section>"
    if marker in page:
        page = sub_one(re.escape(marker)+r'.*?</section>',lambda _:block,page)
    else:
        page = sub_one(r'(<p class="cta">)',lambda m:block+m[1],page)
    return page


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for spn in PAGES:
        rel = f"kody/spn-{spn}.html"
        path = root/rel
        page = path.read_text(encoding="utf-8")
        result = apply_overrides(rel,page)
        if args.check:
            if result != page:
                raise SystemExit(f"OEM corrections missing: {rel}")
        else:
            path.write_text(result,encoding="utf-8",newline="\n")
    print(f"Checked {len(PAGES)} targeted OEM pages")


if __name__ == "__main__":
    main()
