"""Generates the synthetic demo documents in sample_data/synthetic/. All people, firms and reference numbers are fictional."""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "synthetic")
SQFT = 10.7639
GREY = colors.HexColor("#999999")

def new(fname, title, author, desc, size=A4):
    c = canvas.Canvas(os.path.join(OUT, fname), pagesize=size)
    c.setTitle(title); c.setAuthor(author); c.setCreator("sample_data/generate_synthetic.py")
    c.setSubject("synthetic: true | " + desc)
    c.setKeywords("synthetic: true, demo document, hackathon, fictional issuer")
    c._W, c._H = size
    return c

def footer(c, page=None, total=None):
    c.setFont("Helvetica", 6); c.setFillColor(GREY)
    c.drawString(12*mm, 6*mm, "Demo document")
    if page: c.drawRightString(c._W-12*mm, 6*mm, f"Page {page} of {total}")
    c.setFillColor(colors.black)

def para(c, text, x, y, w, size=9, leading=None, font="Helvetica", color=colors.black):
    st = ParagraphStyle("p", fontName=font, fontSize=size, leading=leading or size*1.3, textColor=color)
    p = Paragraph(text, st); _, h = p.wrap(w, 1000); p.drawOn(c, x, y-h); return y-h

def table(c, data, x, y, widths, hdr=colors.HexColor("#333333"), size=8.5, bold_last=False, zebra=True, align_right_from=1):
    t = Table(data, colWidths=widths)
    st = [("FONT",(0,0),(-1,0),"Helvetica-Bold",size),("FONT",(0,1),(-1,-1),"Helvetica",size),
          ("BACKGROUND",(0,0),(-1,0),hdr),("TEXTCOLOR",(0,0),(-1,0),colors.white),
          ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#bbbbbb")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
          ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]
    if align_right_from is not None: st.append(("ALIGN",(align_right_from,1),(-1,-1),"RIGHT"))
    if zebra:
        for r in range(1,len(data)):
            if r%2==0: st.append(("BACKGROUND",(0,r),(-1,r),colors.HexColor("#f3f3f3")))
    if bold_last: st.append(("FONT",(0,-1),(-1,-1),"Helvetica-Bold",size))
    t.setStyle(TableStyle(st)); _, h = t.wrap(0,0); t.drawOn(c, x, y-h); return y-h

def ftin(m):
    inches = round(m/0.0254); return f"{inches//12}'{inches%12}\""

# ---------------- Kelso floor data (NIA, measured survey) -----------------
FLOORS = [  # name, NIA m2, GIA m2, rooms [(label, x, y, w, d)] metres in a 9.0 x 7.2 footprint
 ("Lower Ground Floor", 42.8, 60.9, [("Office 1",0,2.6,5.2,4.6),("Office 2",5.2,3.6,3.8,3.6),("Kitchen",5.2,0,2.0,2.05),("Store",0,0,2.6,2.6),("WC",7.2,0,1.8,1.6),("Stair",2.6,0,2.6,2.6),("Lobby",7.2,1.6,1.8,2.0)]),
 ("Ground Floor",       48.6, 64.4, [("Office 3",0,2.6,5.2,4.6),("Office 4",5.2,3.4,3.8,3.8),("Meeting",5.2,0,2.4,3.4),("Entrance Hall",2.6,0,2.6,2.6),("WC",0,0,1.4,2.6),("Store",1.4,0,1.2,2.6),("Cpd",7.6,0,1.4,3.4)]),
 ("First Floor",        47.9, 63.8, [("Office 5",0,2.6,5.2,4.6),("Office 6",5.2,3.5,3.8,3.7),("Office 7",5.2,0,3.8,3.5),("Landing",2.6,0,2.6,2.6),("WC",0,0,2.6,2.6)]),
 ("Second Floor",       38.3, 59.1, [("Office 8",0,2.6,5.2,4.6),("Office 9",5.2,3.5,3.8,3.7),("Kitchenette",5.2,0,2.2,3.5),("Landing",2.6,0,2.6,2.6),("WC",0,0,2.6,2.6),("Plant",7.4,0,1.6,3.5)]),
]
NIA = round(sum(f[1] for f in FLOORS),1); GIA = round(sum(f[2] for f in FLOORS),1)
assert NIA == 177.6 and GIA == 248.2, (NIA, GIA)
def sf(m2): return round(m2*SQFT)

def draw_plan(c, x0, y0, scale, floor):
    name, nia, gia, rooms = floor
    c.setFont("Helvetica-Bold", 10); c.drawString(x0, y0+7.2*scale+16, name.upper())
    c.setFont("Helvetica", 7.5); c.drawString(x0, y0+7.2*scale+6, f"NIA {nia:.1f} m² ({sf(nia):,} sq ft)   GIA {gia:.1f} m² ({sf(gia):,} sq ft)")
    for (lab,x,y,w,d) in rooms:
        X,Y,Wd,D = x0+x*scale, y0+y*scale, w*scale, d*scale
        fill = colors.HexColor("#e8e8e8") if lab in ("Stair","Landing","Lobby","Entrance Hall","Cpd","Plant") else colors.white
        c.setFillColor(fill); c.setStrokeColor(colors.black); c.setLineWidth(0.8); c.rect(X,Y,Wd,D,fill=1,stroke=1)
        c.setFillColor(colors.black)
        if lab in ("Stair",):
            for i in range(1,8): c.line(X+i*Wd/8, Y+2, X+i*Wd/8, Y+D-2)
        fs = 7.5 if Wd>45 else 6
        if lab=="Stair":
            c.setFillColor(colors.white); c.rect(X+Wd/2-14, Y+D/2-15, 28, 25, fill=1, stroke=0); c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", fs); c.drawCentredString(X+Wd/2, Y+D/2+3, lab)
        if w*d>=6:
            c.setFont("Helvetica", 6); c.drawCentredString(X+Wd/2, Y+D/2-5, f"{w:.2f} x {d:.2f} m")
            c.drawCentredString(X+Wd/2, Y+D/2-12, f"{ftin(w)} x {ftin(d)}")
    c.setLineWidth(2.2); c.rect(x0,y0,9.0*scale,7.2*scale,fill=0,stroke=1); c.setLineWidth(0.8)
    # overall dimension lines
    c.setFont("Helvetica",6.5); c.line(x0, y0-8, x0+9*scale, y0-8)
    c.line(x0,y0-11,x0,y0-5); c.line(x0+9*scale,y0-11,x0+9*scale,y0-5)
    c.drawCentredString(x0+4.5*scale, y0-17, "9.00 m (29'6\") external")
    c.saveState(); c.translate(x0-8, y0+3.6*scale); c.rotate(90); c.drawCentredString(0,4,"7.20 m (23'7\")"); c.restoreState()
    c.line(x0-8,y0,x0-8,y0+7.2*scale)

def survey_header(c, sub):
    W,H=c._W,c._H
    c.setFillColor(colors.HexColor("#1f4e5f")); c.rect(0,H-22*mm,W,22*mm,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",15); c.drawString(14*mm,H-11*mm,"HOLLOWAY & REID")
    c.setFont("Helvetica",8); c.drawString(14*mm,H-16.5*mm,"Chartered Measured Building Surveyors  ·  4 Northgate Mews, Bath BA1 5AJ  ·  01225 000 418")
    c.setFont("Helvetica-Bold",11); c.drawRightString(W-14*mm,H-11*mm,"MEASURED SURVEY")
    c.setFont("Helvetica",8); c.drawRightString(W-14*mm,H-16.5*mm,sub)
    c.setFillColor(colors.black)

def title_block(c, x, y, rows):
    w=82*mm; h=len(rows)*5*mm
    c.setLineWidth(0.6); c.rect(x,y,w,h)
    for i,(k,v) in enumerate(rows):
        yy=y+h-(i+1)*5*mm; c.line(x,yy,x+w,yy) if i<len(rows)-1 else None
        c.setFont("Helvetica",6.5); c.setFillColor(colors.HexColor("#555555")); c.drawString(x+2*mm,yy+1.7*mm,k)
        c.setFillColor(colors.black); c.setFont("Helvetica-Bold",7.5); c.drawString(x+26*mm,yy+1.7*mm,v)

def kelso_survey():
    c = new("kelso-villa_measured-survey_holloway-reid_2026-09.pdf","Kelso Villa - Measured Survey and Floor Plans (Rev A)","Holloway & Reid Chartered Surveyors (fictional)",
            "Fictional measured survey of Kelso Villa, Bath BA1 3AU, Sept 2026. Per-floor NIA sums to 177.6 m2 / 1,912 sq ft (vs brochure 185 m2 / 1,990 sq ft); GIA 248.2 m2 / 2,672 sq ft; site plan shows 6 marked parking bays.", landscape(A4))
    W,H=c._W,c._H; TOT=3
    # page 1: schedule
    survey_header(c,"Job ref HR/26/0917  ·  Rev A  ·  18 September 2026")
    y=H-34*mm
    c.setFont("Helvetica-Bold",16); c.drawString(14*mm,y,"Kelso Villa, Upper Bristol Road, Bath BA1 3AU"); y-=7*mm
    c.setFont("Helvetica",9.5); c.drawString(14*mm,y,"Schedule of areas: Grade II listed office building, four storeys (lower ground to second floor)"); y-=8*mm
    rows=[["Floor","NIA m²","NIA sq ft","GIA m²","GIA sq ft","Ceiling height"]]
    hts=["2.38 m","3.12 m","2.95 m","2.61 m"]
    for f,h in zip(FLOORS,hts): rows.append([f[0],f"{f[1]:.1f}",f"{sf(f[1]):,}",f"{f[2]:.1f}",f"{sf(f[2]):,}",h])
    rows.append(["Total (all floors)",f"{NIA:.1f}",f"{sf(NIA):,}",f"{GIA:.1f}",f"{sf(GIA):,}",""])
    y=table(c,rows,14*mm,y,[52*mm,24*mm,24*mm,24*mm,24*mm,26*mm],hdr=colors.HexColor("#1f4e5f"),size=9,bold_last=True)
    y-=8*mm
    y=para(c,"<b>Basis of measurement.</b> Measured in accordance with the RICS Code of Measuring Practice (6th edition). Net Internal Area (NIA) excludes stairwells, lift and plant areas, toilets, internal structural walls and areas with headroom below 1.5 m. Gross Internal Area (GIA) is measured to the internal face of the perimeter walls at each floor level. Conversions use 1 m² = 10.7639 sq ft; totals are summed in m² and then converted.",14*mm,y,170*mm,8.5)
    y-=4*mm
    y=para(c,"<b>Note to client.</b> The NIA recorded here (177.6 m² / 1,912 sq ft) is lower than the 185 m² / 1,990 sq ft quoted in current marketing particulars. The difference arises mainly on the second floor, where we exclude the eaves zone with headroom below 1.5 m and the plant cupboard.",14*mm,y,170*mm,8.5)
    y-=4*mm
    y=para(c,"<b>Parking.</b> Six (6) marked parking bays within the rear courtyard demised with the building, as shown on drawing HR/26/0917/03.",14*mm,y,170*mm,8.5)
    title_block(c,W-96*mm,40*mm,[("Client","Kelso Villa Holdings Ltd"),("Surveyed by","T. Okonkwo-Blake MRICS"),("Checked by","H. Vance FRICS"),("Date of survey","9 September 2026"),("Issued","18 September 2026"),("Drawing","HR/26/0917/00 Rev A"),("Status","FINAL – for information")])
    # site plan HR/26/0917/03
    bx,by=14*mm,15*mm; c.setFont("Helvetica-Bold",9); c.drawString(bx,by+51*mm,"Site plan: rear courtyard parking (drawing HR/26/0917/03, not to scale)")
    c.setLineWidth(0.6); c.rect(bx,by,170*mm,48*mm)
    c.setFillColor(colors.HexColor("#d8d2c4")); c.rect(bx,by+32*mm,50*mm,16*mm,fill=1); c.setFillColor(colors.black); c.setFont("Helvetica-Bold",8); c.drawCentredString(bx+25*mm,by+39*mm,"KELSO VILLA")
    for i in range(6):
        x=bx+62*mm+i*17.5*mm; c.setFillColor(colors.white); c.setDash(3,2); c.rect(x,by+5*mm,14*mm,26*mm,fill=1); c.setDash()
        c.setFillColor(colors.black); c.setFont("Helvetica-Bold",11); c.drawCentredString(x+7*mm,by+16*mm,str(i+1))
        c.setFont("Helvetica",6); c.drawCentredString(x+7*mm,by+10*mm,"2.4 x 4.8 m")
    c.setFont("Helvetica",7.5); c.drawString(bx+3*mm,by+4*mm,"Gated access from A4 Upper Bristol Road")
    c.drawString(bx+3*mm,by+24*mm,"6 marked bays (yellow box lining)")
    footer(c,1,TOT); c.showPage()
    # page 2: LG + G plans
    for pg,(fa,fb) in ((2,(0,1)),(3,(2,3))):
        survey_header(c,f"Floor plans  ·  Drawing HR/26/0917/0{pg-1}  ·  Rev A")
        sc=12.5*mm
        draw_plan(c,22*mm,58*mm,sc,FLOORS[fa]); draw_plan(c,22*mm+9*sc+24*mm,58*mm,sc,FLOORS[fb])
        c.setFont("Helvetica",7); c.drawString(22*mm,24*mm,"Scale 1:80 at A4 (approx.). Room dimensions are wall-to-wall internal. Shaded areas are excluded from NIA.")
        # north arrow + scale bar
        nx,ny=W-24*mm,28*mm
        c.line(nx,ny,nx,ny+12*mm); c.line(nx,ny+12*mm,nx-2*mm,ny+8*mm); c.line(nx,ny+12*mm,nx+2*mm,ny+8*mm); c.setFont("Helvetica-Bold",8); c.drawCentredString(nx,ny+14*mm,"N")
        for i in range(5):
            c.setFillColor(colors.black if i%2==0 else colors.white); c.rect(22*mm+i*sc,32*mm,sc,2*mm,fill=1)
        c.setFillColor(colors.black); c.setFont("Helvetica",6.5); c.drawString(22*mm,36*mm,"0                                                                         5 m")
        if pg==3:
            # site plan inset with parking bays
            sx,sy=W-80*mm,H-120*mm
        footer(c,pg,TOT); c.showPage()
    c.save()

def kelso_site_plan_on_p3():
    pass

# ---------------- Kelso EPC (non-domestic) ----------------
def epc_bands(c, x, y, current, potential, domestic=True):
    bands=[("A","92+" if domestic else "0-25","#008054"),("B","81-91" if domestic else "26-50","#19b459"),("C","69-80" if domestic else "51-75","#8dce46"),("D","55-68" if domestic else "76-100","#ffd500"),("E","39-54" if domestic else "101-125","#fcaa65"),("F","21-38" if domestic else "126-150","#ef8023"),("G","1-20" if domestic else "Over 150","#e9153b")]
    bh=7.2*mm
    c.setFont("Helvetica-Bold",8); c.drawString(x,y+2*mm,"Score  Energy rating"); c.drawString(x+112*mm,y+2*mm,"Current"); c.drawString(x+140*mm,y+2*mm,"Potential")
    for i,(b,r,col) in enumerate(bands):
        yy=y-(i+1)*bh; w=(40+i*10)*mm
        c.setFillColor(colors.HexColor(col)); c.rect(x,yy+0.6*mm,w,bh-1.2*mm,fill=1,stroke=0)
        c.setFillColor(colors.black if b in "CDE" else colors.white); c.setFont("Helvetica-Bold",8); c.drawString(x+2*mm,yy+2.4*mm,r)
        c.setFont("Helvetica-Bold",12); c.drawRightString(x+w-3*mm,yy+2*mm,b)
        for val,col_x in ((current,112*mm),(potential,140*mm)):
            if val[1]==b:
                c.setFillColor(colors.HexColor(col)); p=c.beginPath(); X=x+col_x
                p.moveTo(X,yy+bh/2); p.lineTo(X+5*mm,yy+bh-0.6*mm); p.lineTo(X+24*mm,yy+bh-0.6*mm); p.lineTo(X+24*mm,yy+0.6*mm); p.lineTo(X+5*mm,yy+0.6*mm); p.close(); c.drawPath(p,fill=1,stroke=0)
                c.setFillColor(colors.black if b in "CDE" else colors.white); c.setFont("Helvetica-Bold",10); c.drawString(X+6*mm,yy+2.2*mm,f"{val[0]} {b}")
    c.setFillColor(colors.black); return y-7*bh

def epc_header(c, kind):
    W,H=c._W,c._H
    c.setFont("Helvetica-Bold",19); c.drawString(15*mm,H-22*mm,"Energy performance certificate (EPC)")
    c.setFont("Helvetica",9); c.drawString(15*mm,H-28*mm,kind)
    c.setLineWidth(3); c.setStrokeColor(colors.HexColor("#1d70b8")); c.line(15*mm,H-31*mm,W-15*mm,H-31*mm); c.setStrokeColor(colors.black); c.setLineWidth(0.5)

def kv_box(c,x,y,w,rows,size=9):
    data=[[Paragraph(f"<b>{k}</b>",ParagraphStyle("k",fontSize=size,leading=size*1.25)),Paragraph(v,ParagraphStyle("v",fontSize=size,leading=size*1.25))] for k,v in rows]
    t=Table(data,colWidths=[w*0.42,w*0.58]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f3f2f1")),("LINEBELOW",(0,0),(-1,-2),0.4,colors.white),("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
    _,h=t.wrap(0,0); t.drawOn(c,x,y-h); return y-h

def kelso_epc():
    c=new("kelso-villa_epc-nondomestic_2026-08.pdf","Energy performance certificate - Kelso Villa (non-domestic)","EPC register extract (fictional assessor)",
          "Fictional non-domestic EPC for Kelso Villa, Bath BA1 3AU. Rating C (asset rating 58) vs B in both Carter Jonas brochures. Total useful floor area 239 m2 (EPC basis).")
    W,H=c._W,c._H
    epc_header(c,"Non-domestic building  ·  register extract")
    y=H-38*mm
    y=kv_box(c,15*mm,y,95*mm,[("Address","Kelso Villa<br/>Upper Bristol Road<br/>BATH<br/>BA1 3AU"),("Property type","Offices and workshop businesses"),("Total useful floor area","239 square metres"),("Building complexity (NOS level)","3")])
    kv_box(c,118*mm,H-38*mm,77*mm,[("Certificate number","9417-3082-6651-2049-7735"),("Date of assessment","27 August 2026"),("Date of certificate","2 September 2026"),("Valid until","1 September 2036"),("Register checked","10 November 2026")])
    y-=8*mm
    c.setFont("Helvetica-Bold",13); c.drawString(15*mm,y,"Energy rating and score"); y-=6*mm
    y=para(c,"This property’s current energy rating is <b>C</b>. Properties are given a rating from A+ (most efficient) to G (least efficient). Under 0 = A+; for non-domestic buildings a lower score is better.",15*mm,y,180*mm,9)
    y-=8*mm
    y=epc_bands(c,15*mm,y,(58,"C"),(41,"B"),domestic=False)
    y-=8*mm
    c.setFont("Helvetica-Bold",13); c.drawString(15*mm,y,"How this property compares to others"); y-=3*mm
    y=table(c,[["Benchmark","Score","Rating"],["If newly built","29","B"],["If typical of the existing stock","71","C"],["This building (asset rating)","58","C"]],15*mm,y,[90*mm,30*mm,30*mm],hdr=colors.HexColor("#1d70b8"))
    y-=8*mm
    c.setFont("Helvetica-Bold",13); c.drawString(15*mm,y,"Breakdown of this property’s energy performance"); y-=3*mm
    y=table(c,[["Feature","Detail"],["Main heating fuel","Natural gas"],["Building environment","Heating and natural ventilation"],["Assessment level","3"],["Building emission rate (kgCO2e/m² per year)","41.62"],["Primary energy use (kWh/m² per year)","233"]],15*mm,y,[90*mm,90*mm],hdr=colors.HexColor("#1d70b8"),align_right_from=None)
    y-=8*mm
    y=kv_box(c,15*mm,y,180*mm,[("Energy assessor","Mr Daniel Ferreira-Holt"),("Assessor’s accreditation number","QX-EA-204817 (fictional scheme)"),("Employer","Avonvale Energy Surveys Ltd, Bath"),("Assessor’s declaration","The assessor is not related to the owner of the property.")],8.5)
    footer(c,1,1); c.save()

# ---------------- Kelso title register summary ----------------
def kelso_title():
    c=new("kelso-villa_land-registry-title-summary_2026-11.pdf","Official copy (summary) of register of title ST482917","Land registry title extract (fictional)",
          "Fictional Land Registry title summary for Kelso Villa. Freehold, title absolute; notice of a 10-year lease of the lower ground floor dated 1 Sept 2026; restrictive covenant limiting use to offices; parking rights for 6 vehicles.")
    W,H=c._W,c._H
    c.setFont("Helvetica-Bold",15); c.drawString(15*mm,H-20*mm,"HM Land Registry")
    c.setFont("Helvetica",10); c.drawString(15*mm,H-26*mm,"Official copy (summary) of register of title")
    c.setFont("Helvetica-Bold",10); c.drawRightString(W-15*mm,H-20*mm,"Title number ST482917")
    c.setFont("Helvetica",8.5); c.drawRightString(W-15*mm,H-26*mm,"Edition date 03.09.2026")
    c.drawRightString(W-15*mm,H-31*mm,"Search date and time: 10 November 2026 at 09:14:52")
    c.line(15*mm,H-34*mm,W-15*mm,H-34*mm)
    y=H-40*mm
    y=para(c,"This is a summary of the register. It is not an official copy and should not be relied upon as such. This summary was produced from the register as at the search date shown above. Entries are numbered as in the full register.",15*mm,y,180*mm,8,color=colors.HexColor("#555555"))
    def section(y,letter,name,entries):
        y-=6*mm; c.setFillColor(colors.HexColor("#e7e7e7")); c.rect(15*mm,y-2*mm,180*mm,7*mm,fill=1,stroke=0); c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold",10); c.drawString(17*mm,y,f"{letter}: {name}"); y-=5*mm
        for n,t in entries:
            c.setFont("Helvetica-Bold",8.5); c.drawString(17*mm,y-9,f"{n}")
            y=para(c,t,25*mm,y,168*mm,8.5)-2.5*mm
        return y
    y=section(y,"A","Property Register",[("1","(18 June 1998) The Freehold land shown edged with red on the plan of the above Title filed at the Registry and being Kelso Villa, Upper Bristol Road, Bath (BA1 3AU)."),
        ("2","(18 June 1998) The land has the benefit of the rights granted by a Conveyance dated 4 March 1987, including a right of way on foot and with vehicles over the gated access way shown tinted brown on the title plan."),
        ("3","(18 June 1998) The land includes the parking area at the rear shown edged and numbered blue on the title plan, comprising <b>six parking spaces numbered 1 to 6</b>.")])
    y=section(y,"B","Proprietorship Register",[("","<b>Title absolute</b>"),("1","(3 March 2019) PROPRIETOR: KELSO VILLA HOLDINGS LIMITED (Co. Regn. No. 11904417, fictional) of 12 Queen Square Place, Bath BA1 2HN."),
        ("2","(3 March 2019) The price stated to have been paid on 14 February 2019 was £545,000."),
        ("3","(3 March 2019) RESTRICTION: No disposition of the registered estate by the proprietor of the registered estate is to be registered without a written consent signed by the proprietor for the time being of the charge dated 14 February 2019 in favour of Severnbank Commercial Finance Limited referred to in the Charges Register.")])
    y=section(y,"C","Charges Register",[("1","(18 June 1998) A Conveyance of the land in this title dated 4 March 1987 made between (1) The Gas Light and Coke Pension Trustees Limited and (2) Avonleigh Properties Limited contains the following covenant: <i>“Not to use the property or any part of it otherwise than as offices within Class E(g)(i) and not to erect any building or structure on the parking area.”</i>"),
        ("2","(14 February 2019) REGISTERED CHARGE dated 14 February 2019."),
        ("3","(3 September 2026) <b>NOTICE of a lease dated 1 September 2026 of the lower ground floor</b> of Kelso Villa for a term of 10 years from and including 1 September 2026, together with the right to use parking space numbered 1. NOTE: Copy filed under ST482917."),
        ("4","(3 September 2026) Lessee’s title registered under ST509334.")])
    y-=4*mm
    para(c,"End of register summary. Fictional title number and parties for demonstration.",15*mm,y,180*mm,7.5,color=GREY)
    footer(c,1,1); c.save()

# ---------------- Kelso portal listing snapshot ----------------
def kelso_listing():
    c=new("kelso-villa_portal-listing-snapshot_2026-11.pdf","PropNest Commercial listing snapshot - Kelso Villa, Bath","PropNest Commercial (fictional portal)",
          "Fictional property portal listing captured 9 Nov 2026, still showing freehold offers £700,000 and lower ground floor to let at £9,400 pa (stale against the Oct 2026 brochure and the Sept 2026 lease).")
    W,H=c._W,c._H
    c.setFont("Helvetica",7); c.setFillColor(GREY); c.drawString(12*mm,H-8*mm,"https://www.propnest-commercial.example/listing/PNC-7731804   ·   captured 09/11/2026 16:42 GMT"); c.setFillColor(colors.black)
    c.setFillColor(colors.HexColor("#0a7d6b")); c.rect(0,H-24*mm,W,13*mm,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",16); c.drawString(14*mm,H-19.5*mm,"PropNest"); c.setFont("Helvetica",11); c.drawString(43*mm,H-19.5*mm,"Commercial")
    c.setFont("Helvetica",8.5); c.drawRightString(W-14*mm,H-19*mm,"Buy   ·   Rent   ·   Sold prices   ·   Sign in")
    c.setFillColor(colors.black); c.setFont("Helvetica",8); c.drawString(14*mm,H-31*mm,"Home  >  Commercial  >  Bath  >  Offices  >  Kelso Villa")
    # photo placeholder
    c.setFillColor(colors.HexColor("#c9c3b5")); c.rect(14*mm,H-118*mm,112*mm,80*mm,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#8a8170")); 
    c.rect(48*mm,H-112*mm,44*mm,62*mm,fill=1,stroke=0)
    c.setFillColor(colors.white)
    for r in range(4):
        for k in range(2): c.rect((56+k*18)*mm,(H/mm-108+r*14)*mm,9*mm,10*mm,fill=1,stroke=0)
    c.setFont("Helvetica",7); c.drawString(16*mm,H-116*mm,"1 / 9  photos")
    # price panel
    px=132*mm; c.setFillColor(colors.black)
    c.setFont("Helvetica",8.5); c.drawString(px,H-44*mm,"Freehold offers in excess of")
    c.setFont("Helvetica-Bold",24); c.drawString(px,H-55*mm,"£700,000")
    c.setFont("Helvetica-Bold",11); c.drawString(px,H-64*mm,"Office for sale or to let")
    c.setFont("Helvetica",9); c.drawString(px,H-70*mm,"Kelso Villa, Upper Bristol Road, Bath BA1 3AU")
    y=table(c,[["Key facts",""],["Size","2,700 sq ft"],["Tenure","Freehold"],["EPC","B"],["Parking","1 space per floor"],["Also to let","Lower ground: £9,400 pa"],["Added on","14/04/2026"],["Reduced on","—"]],px,H-75*mm,[24*mm,40*mm],hdr=colors.HexColor("#0a7d6b"),align_right_from=None,size=8)
    y=H-128*mm
    c.setFont("Helvetica-Bold",12); c.drawString(14*mm,y,"Description"); y-=3*mm
    y=para(c,"Kelso Villa is a Grade II listed former house of the Gas Lighting and Light Coke Company manager, used as offices for many years and set within a courtyard development of other offices. The floors are available by way of new leases at £9,400 per annum, exclusive, for each floor, with one parking space per floor. <b>The lower ground floor (468 sq ft) is currently available.</b> Alternatively freehold offers will be considered at £700,000, subject to existing tenancies.",14*mm,y,180*mm,9)
    y-=5*mm
    c.setFont("Helvetica-Bold",12); c.drawString(14*mm,y,"Features"); y-=2*mm
    y=para(c,"• City centre location &nbsp; • Gated rear courtyard with allocated parking &nbsp; • Gas central heating &nbsp; • Security alarm &nbsp; • Fibre available",14*mm,y,180*mm,9)
    y-=6*mm
    c.setFillColor(colors.HexColor("#f2f2f2")); c.rect(14*mm,y-24*mm,180*mm,24*mm,fill=1,stroke=0); c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold",10); c.drawString(18*mm,y-7*mm,"Marketed by")
    c.setFont("Helvetica",9); c.drawString(18*mm,y-13*mm,"Carter Jonas, Bath  ·  Listing feed reference CJ-BTH-98889981")
    c.drawString(18*mm,y-19*mm,"Listing ID PNC-7731804  ·  Last updated by agent feed: 16/04/2026")
    para(c,"Listing information is supplied by the marketing agent. PropNest Commercial does not verify listing details.",14*mm,y-30*mm,180*mm,7,color=GREY)
    footer(c,1,1); c.save()

# ---------------- Kelso parking allocation schedule ----------------
def kelso_parking():
    c=new("kelso-villa_parking-allocation-schedule_2026-10.pdf","Kelso Villa - Parking Allocation Schedule (October 2026)","Abbeygate Estate Management Ltd (fictional)",
          "Fictional managing agent parking allocation schedule, 6 Oct 2026: 5 allocated spaces; bay 6 reclassified as bin store/turning area. True conflict with 6 spaces in survey, title and October brochure.")
    W,H=c._W,c._H
    c.setFont("Helvetica-Bold",17); c.setFillColor(colors.HexColor("#6b2d5c")); c.drawString(15*mm,H-20*mm,"ABBEYGATE"); c.setFont("Helvetica",9); c.drawString(15*mm,H-25*mm,"Estate Management Ltd")
    c.setFillColor(colors.black); c.setFont("Helvetica",8)
    for i,t in enumerate(["7 Chapel Row, Bath BA1 1HN","01225 000 771","property@abbeygate-em.example"]): c.drawRightString(W-15*mm,H-16*mm-i*4*mm,t)
    c.line(15*mm,H-30*mm,W-15*mm,H-30*mm)
    y=H-40*mm
    c.setFont("Helvetica-Bold",14); c.drawString(15*mm,y,"Parking Allocation Schedule"); y-=6*mm
    c.setFont("Helvetica",9.5); c.drawString(15*mm,y,"Property: Kelso Villa, Upper Bristol Road, Bath BA1 3AU (rear courtyard)"); y-=5*mm
    c.drawString(15*mm,y,"Schedule ref: AEM/KV/PAS/04   ·   Issue 4   ·   Effective 6 October 2026   ·   Supersedes Issue 3 (12 January 2025)"); y-=8*mm
    y=table(c,[["Bay","Allocated to","Basis","Since","EV charger"],["1","Lower ground floor tenant","Lease 01/09/2026","01/09/2026","No"],["2","Ground floor tenant","Licence","15/03/2023","No"],["3","First floor tenant","Licence","15/03/2023","No"],["4","Second floor tenant","Licence","02/05/2024","No"],["5","Landlord / visitors","Landlord","—","Ducting only"],["6",Paragraph("<b>NOT ALLOCATED</b> – reclassified as bin store and turning area (fire access)",ParagraphStyle("c",fontSize=8.5,leading=10.5)),"—","06/10/2026","—"]],15*mm,y,[12*mm,78*mm,32*mm,24*mm,24*mm],hdr=colors.HexColor("#6b2d5c"),align_right_from=None,size=8.5)
    y-=6*mm
    c.setFont("Helvetica-Bold",11); c.drawString(15*mm,y,"Total allocated parking spaces: 5 (five)"); y-=8*mm
    # courtyard sketch
    c.setFont("Helvetica-Bold",9); c.drawString(15*mm,y,"Courtyard layout (not to scale)"); y-=4*mm
    bx,by=15*mm,y-48*mm; c.setStrokeColor(colors.black); c.rect(bx,by,180*mm,48*mm)
    c.setFillColor(colors.HexColor("#d8d2c4")); c.rect(bx,by+34*mm,60*mm,14*mm,fill=1); c.setFillColor(colors.black); c.setFont("Helvetica-Bold",8); c.drawCentredString(bx+30*mm,by+40*mm,"KELSO VILLA")
    for i in range(6):
        x=bx+70*mm+i*18*mm
        if i==5: c.setFillColor(colors.HexColor("#f2d0d0"))
        else: c.setFillColor(colors.HexColor("#fff6c9"))
        c.rect(x,by+4*mm,15*mm,28*mm,fill=1); c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold",11); c.drawCentredString(x+7.5*mm,by+20*mm,str(i+1))
        if i==5: c.setFont("Helvetica",6.5); c.drawCentredString(x+7.5*mm,by+12*mm,"BINS /"); c.drawCentredString(x+7.5*mm,by+8*mm,"TURNING")
    c.setFont("Helvetica",7.5); c.drawString(bx+3*mm,by+4*mm,"Gated access from A4 Upper Bristol Road →")
    y=by-8*mm
    y=para(c,"<b>Notes.</b> (1) Following the fire risk assessment of 22 September 2026, bay 6 can no longer be used for parking because it is required as a turning area for emergency access and for the relocated bin store. (2) Allocations by licence can be varied by the landlord on 28 days’ notice. (3) Bay 1 is granted under the lease of the lower ground floor dated 1 September 2026.",15*mm,y,180*mm,8.5)
    y-=10*mm
    c.setFont("Helvetica",9); c.drawString(15*mm,y,"Signed for Abbeygate Estate Management Ltd"); c.setFont("Helvetica-Oblique",14); c.drawString(15*mm,y-9*mm,"R. Penhallow")
    c.setFont("Helvetica",8.5); c.drawString(15*mm,y-14*mm,"Rhiannon Penhallow MIRPM, Property Manager  ·  6 October 2026")
    footer(c,1,1); c.save()

# ---------------- St Huberts Close: schedule of finishes ----------------
def sh_finishes():
    c=new("st-huberts-close_schedule-of-finishes_chiltern-vale_2026-09.pdf","St Huberts Close - Schedule of Finishes, house types A-E (Rev C)","Chiltern Vale Developments Ltd (fictional)",
          "Fictional development-wide schedule of finishes for St Huberts Close, Gerrards Cross, Rev C Sept 2026. States all en-suites have walk-in showers (development scope) while the No. 59 brochure states a principal en-suite bathroom (unit scope). Lists No. 59 as house type E (5 bed).")
    W,H=c._W,c._H; TOT=2
    def hdr():
        c.setFillColor(colors.HexColor("#2e4a2e")); c.rect(0,H-20*mm,W,20*mm,fill=1,stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold",14); c.drawString(15*mm,H-11*mm,"CHILTERN VALE DEVELOPMENTS")
        c.setFont("Helvetica",8); c.drawString(15*mm,H-16*mm,"Oak House, 3 Station Approach, Gerrards Cross SL9 0AA (fictional)")
        c.setFont("Helvetica-Bold",9); c.drawRightString(W-15*mm,H-11*mm,"SCHEDULE OF FINISHES"); c.setFont("Helvetica",8); c.drawRightString(W-15*mm,H-16*mm,"Doc CVD-SHC-SOF  ·  Rev C  ·  15 September 2026")
        c.setFillColor(colors.black)
    hdr(); y=H-30*mm
    c.setFont("Helvetica-Bold",15); c.drawString(15*mm,y,"St Huberts Close, Gerrards Cross"); y-=6*mm
    c.setFont("Helvetica",9.5); c.drawString(15*mm,y,"Specification applicable to all house types A–E unless stated otherwise in the plot schedule (section 4)"); y-=7*mm
    secs=[("1. Kitchens",[["Units","Shaker-style painted units with soft-close hinges; maple-effect option on type E"],["Worktops","20 mm quartz with upstand; 1½ bowl stainless steel undermount sink"],["Appliances","Integrated oven, combination microwave, induction hob, extractor, fridge-freezer and dishwasher"]]),
          ("2. Bathrooms and en-suites",[["Family bathroom","White suite with bath, thermostatic shower over bath and glass screen"],["En-suites","<b>All en-suites are fitted with walk-in showers with low-profile trays and glass screens. No en-suite has a bath.</b>"],["Tiling","Full height to wet areas; half height elsewhere; porcelain floor tiles"],["Sanitaryware","Wall-hung WCs with concealed cisterns; chrome fittings throughout"]]),
          ("3. Heating, electrical and external",[["Heating","Gas-fired condensing boiler with radiators; underfloor heating to ground floor of types D and E"],["Electrical","LED downlights to kitchen and bathrooms; USB sockets to kitchen and bedrooms"],["Garaging","Double garage to types C, D and E; single garage to types A and B"],["EV charging","7 kW charge point to every garage"]])]
    st=ParagraphStyle("t",fontSize=8.5,leading=11)
    for name,rows in secs:
        c.setFont("Helvetica-Bold",11); c.drawString(15*mm,y,name); y-=2.5*mm
        data=[[Paragraph(f"<b>{a}</b>",st),Paragraph(b,st)] for a,b in rows]
        t=Table(data,colWidths=[38*mm,142*mm]); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#bbbbbb")),("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eef2ea"))]))
        _,h=t.wrap(0,0); t.drawOn(c,15*mm,y-h); y-=h+7*mm
    para(c,"This schedule describes the standard specification for the development. Purchasers should check the plot schedule and the individual property, as finishes may vary between plots and may have been altered by subsequent owners.",15*mm,y,180*mm,8,color=colors.HexColor("#555555"))
    footer(c,1,TOT); c.showPage()
    hdr(); y=H-30*mm
    c.setFont("Helvetica-Bold",11); c.drawString(15*mm,y,"4. House types and plot schedule"); y-=3*mm
    y=table(c,[["Type","Name","Bedrooms","Bathrooms (incl. en-suite)","Receptions","Garage","GIA sq ft"],["A","The Bulstrode","3","2","2","Single","1,420"],["B","The Chalfont","4","2","2","Single","1,760"],["C","The Denham","4","2","2","Double","2,098"],["D","The Fulmer","5","3","3","Double","2,512"],["E","The Hedgerley","5","3","5","Double","2,848"]],15*mm,y,[14*mm,34*mm,22*mm,40*mm,22*mm,20*mm,26*mm],hdr=colors.HexColor("#2e4a2e"),size=8.5,align_right_from=2)
    y-=6*mm
    y=table(c,[["Plot / No.","House type","Handed","Notes"],["51","C","No","—"],["53","D","Yes","—"],["55","C","Yes","—"],["57","D","No","Conservatory added (owner)"],["59","E","No","Principal en-suite and guest en-suite as standard type E"],["61","E","Yes","—"]],15*mm,y,[24*mm,26*mm,20*mm,110*mm],hdr=colors.HexColor("#2e4a2e"),align_right_from=None,size=8.5)
    y-=8*mm
    y=para(c,"<b>Approval.</b> Issued for sales information. Revision C supersedes Revision B (2 March 2026): updated EV charging and kitchen worktop wording.",15*mm,y,180*mm,8.5)
    y-=8*mm
    c.setFont("Helvetica",9); c.drawString(15*mm,y,"Signed for Chiltern Vale Developments Ltd"); c.setFont("Helvetica-Oblique",14); c.drawString(15*mm,y-9*mm,"M. Ashdown")
    c.setFont("Helvetica",8.5); c.drawString(15*mm,y-14*mm,"Marcus Ashdown, Technical Director  ·  15 September 2026")
    footer(c,2,TOT); c.save()

# ---------------- 59 St Huberts Close: price change instruction ----------------
def sh_price():
    c=new("59-st-huberts-close_price-change-instruction_2026-11.pdf","59 St Huberts Close - Instruction to amend guide price","Harcourt Lane LLP (fictional) for the vendors",
          "Fictional formal vendor instruction (tier 4) dated 3 Nov 2026 reducing the guide price of 59 St Huberts Close from £1,458,000 to £1,395,000. Supersedes the April 2026 brochure price; portal not yet updated.")
    W,H=c._W,c._H
    c.setFont("Times-Bold",18); c.drawString(15*mm,H-22*mm,"Harcourt Lane LLP"); c.setFont("Times-Roman",9); c.drawString(15*mm,H-27*mm,"Solicitors  ·  22 Oxford Road, Beaconsfield HP9 1XX (fictional)")
    c.setFont("Helvetica",8.5)
    for i,t in enumerate(["Our ref: HL/PR/7719/JW","Your ref: GC-SHC59","Date: 3 November 2026"]): c.drawRightString(W-15*mm,H-18*mm-i*4.5*mm,t)
    c.line(15*mm,H-32*mm,W-15*mm,H-32*mm)
    y=H-42*mm; c.setFont("Helvetica",10)
    for t in ["The Sales Manager","Residential Sales, Gerrards Cross office","By email"]: c.drawString(15*mm,y,t); y-=5*mm
    y-=4*mm; c.setFont("Helvetica-Bold",11); c.drawString(15*mm,y,"FORMAL INSTRUCTION: AMENDMENT TO GUIDE PRICE"); y-=5*mm
    c.drawString(15*mm,y,"Property: 59 St Huberts Close, Gerrards Cross, Buckinghamshire"); y-=8*mm
    y=para(c,"We act for the joint vendors, Mr Edmund Rowe and Mrs Priya Rowe, in the sale of the above property. Our clients instruct you, with effect from <b>Monday 9 November 2026</b>, to amend the guide price as follows:",15*mm,y,180*mm,10)
    y-=5*mm
    y=table(c,[["","Guide price","Effective"],["Previous (particulars prepared April 2026)","£1,458,000","—"],["Revised","£1,395,000","09/11/2026"],["Change","−£63,000 (−4.3%)",""]],15*mm,y,[90*mm,45*mm,45*mm],hdr=colors.HexColor("#444444"),size=10)
    y-=7*mm
    y=para(c,"Please update the particulars, your website and all portal listings by the effective date and confirm when this has been done. All other terms of your instruction are unchanged. The property remains offered with no onward chain. The revised figure is a guide price, not an asking price, and does not constitute an offer capable of acceptance.",15*mm,y,180*mm,10)
    y-=5*mm
    y=para(c,"This instruction is given with the written authority of both vendors, a copy of which is held on our file.",15*mm,y,180*mm,10)
    y-=14*mm
    c.setFont("Helvetica",10); c.drawString(15*mm,y,"Yours faithfully,"); c.setFont("Helvetica-Oblique",15); c.drawString(15*mm,y-11*mm,"J. Whitcombe")
    c.setFont("Helvetica",9); c.drawString(15*mm,y-17*mm,"Joanna Whitcombe, Partner, for and on behalf of Harcourt Lane LLP")
    c.setFont("Helvetica",7.5); c.setFillColor(colors.HexColor("#555555")); c.drawString(15*mm,22*mm,"Harcourt Lane LLP is a fictional firm created for demonstration. SRA number 000000.")
    footer(c,1,1); c.save()

# ---------------- 59 St Huberts Close: domestic EPC ----------------
def sh_epc():
    c=new("59-st-huberts-close_epc-domestic_2025-06.pdf","Energy performance certificate - 59 St Huberts Close","EPC register extract (fictional assessor)",
          "Fictional domestic EPC for 59 St Huberts Close: band D (64), total floor area 241 m2 on the EPC basis (brochure 264.6 m2 / 2,848 sq ft, basis unspecified). The 4-bed St Huberts Close brochure shows EPC C, a different house.")
    W,H=c._W,c._H
    epc_header(c,"England and Wales  ·  register extract")
    y=H-38*mm
    y=kv_box(c,15*mm,y,95*mm,[("Address","59 St Huberts Close<br/>GERRARDS CROSS<br/>SL9 (postcode not shown)"),("Property type","Detached house"),("Total floor area","241 square metres"),("Rules on letting","Can be let if band E or above")])
    kv_box(c,118*mm,H-38*mm,77*mm,[("Certificate number","6620-1187-4402-9315-2286"),("Date of assessment","11 June 2025"),("Date of certificate","13 June 2025"),("Valid until","12 June 2035"),("Register checked","10 November 2026")])
    y-=8*mm
    c.setFont("Helvetica-Bold",13); c.drawString(15*mm,y,"Energy rating and score"); y-=6*mm
    y=para(c,"This property’s current energy rating is <b>D</b>. It has the potential to be <b>C</b>. The higher the score the lower your fuel bills are likely to be. The average energy rating and score for a property in England and Wales are D (60).",15*mm,y,180*mm,9)
    y-=8*mm
    y=epc_bands(c,15*mm,y,(64,"D"),(78,"C"),domestic=True)
    y-=8*mm
    c.setFont("Helvetica-Bold",13); c.drawString(15*mm,y,"Breakdown of property’s energy performance"); y-=3*mm
    y=table(c,[["Feature","Description","Rating"],["Wall","Cavity wall, as built, insulated (assumed)","Good"],["Roof","Pitched, 150 mm loft insulation","Good"],["Window","Fully double glazed","Average"],["Main heating","Boiler and radiators, mains gas","Good"],["Hot water","From main system","Good"],["Lighting","Low energy lighting in 45% of fixed outlets","Average"],["Floor","Solid, no insulation (assumed)","N/A"]],15*mm,y,[35*mm,110*mm,35*mm],hdr=colors.HexColor("#1d70b8"),align_right_from=None)
    y-=6*mm
    y=para(c,"<b>Floor area basis.</b> EPC total floor area is the heated internal floor area of the dwelling. It excludes the integral double garage and unheated spaces and may include or exclude a conservatory depending on its separation from the dwelling.",15*mm,y,180*mm,8.5)
    y-=5*mm
    kv_box(c,15*mm,y,180*mm,[("Assessor","Ms Harriet Okafor-Lyle"),("Accreditation number","QX-DE-551903 (fictional scheme)"),("Assessor’s declaration","No related party")],8.5)
    footer(c,1,1); c.save()

def kelso_site_plan(c):
    pass

if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    for f in (kelso_survey,kelso_epc,kelso_title,kelso_listing,kelso_parking,sh_finishes,sh_price,sh_epc): f()
    print("ok", sorted(os.listdir(OUT)))
