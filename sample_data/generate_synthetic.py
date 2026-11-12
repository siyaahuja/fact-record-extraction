"""Generates the synthetic demo documents into sample_data/<development>/synthetic_*.pdf. All people, firms and reference numbers are fictional."""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
import os
BASE = os.path.dirname(os.path.abspath(__file__))  # writes into <development>/synthetic_<name>.pdf
SQFT = 10.7639
GREY = colors.HexColor("#999999")

def new(fname, title, author, desc, size=A4):
    dev = "kelso-villa" if fname.startswith("kelso") else "st-huberts-close"
    os.makedirs(os.path.join(BASE, dev), exist_ok=True)
    c = canvas.Canvas(os.path.join(BASE, dev, "synthetic_" + fname), pagesize=size)
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
            "Fictional measured survey of Kelso Villa, Bath BA1 3AU, Sept 2026. Per-floor NIA sums to 177.6 m2 / 1,912 sq ft (vs brochure 185 m2 / 1,990 sq ft); GIA 248.2 m2 / 2,672 sq ft; site plan shows 5 allocated parking bays (bay 6 bin store/turning area); surveyor's note cites the current EPC as band C (cert 9417-3082-6651-2049-7735, 2 Sep 2026).", landscape(A4))
    W,H=c._W,c._H; TOT=4
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
    y=para(c,"<b>Parking.</b> The rear courtyard is lined for six bays. On the date of survey <b>five (5) bays (1 to 5) were in use as allocated parking</b>; bay 6 is marked as bin store and turning area and was not in use for parking. See drawing HR/26/0917/03.",14*mm,y,170*mm,8.5)
    y-=4*mm
    y=para(c,"<b>Energy Performance Certificate.</b> For information, the current non-domestic EPC for the building (certificate 9417-3082-6651-2049-7735, dated 2 September 2026) records an asset rating of 58, <b>band C</b>, and a total useful floor area of 239 m². EPC floor area is calculated on its own basis and is not comparable with the NIA or GIA above.",14*mm,y,170*mm,8.5)
    title_block(c,W-96*mm,22*mm,[("Client","Kelso Villa Holdings Ltd"),("Surveyed by","T. Okonkwo-Blake MRICS"),("Checked by","H. Vance FRICS"),("Date of survey","9 September 2026"),("Issued","18 September 2026"),("Drawing","HR/26/0917/00 Rev A"),("Status","FINAL – for information")])
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
        footer(c,pg,TOT); c.showPage()
    # page 4: site plan
    survey_header(c,"Site plan  ·  Drawing HR/26/0917/03  ·  Rev A")
    bx,by=20*mm,40*mm; BW,BH=W-40*mm,120*mm
    c.setFont("Helvetica-Bold",12); c.drawString(bx,by+BH+8*mm,"REAR COURTYARD: PARKING AS SURVEYED 9 SEPTEMBER 2026")
    c.setLineWidth(1.4); c.rect(bx,by,BW,BH); c.setLineWidth(0.6)
    c.setFillColor(colors.HexColor("#d8d2c4")); c.rect(bx,by+BH-38*mm,70*mm,38*mm,fill=1); c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold",10); c.drawCentredString(bx+35*mm,by+BH-20*mm,"KELSO VILLA"); c.setFont("Helvetica",7.5); c.drawCentredString(bx+35*mm,by+BH-25*mm,"(footprint 9.00 x 7.20 m)")
    bw,bd,gap=24*mm,48*mm,3*mm; x0=bx+BW-6*(bw+gap)-6*mm; yb=by+8*mm
    for i in range(6):
        x=x0+i*(bw+gap)
        if i<5:
            c.setFillColor(colors.HexColor("#fff6c9")); c.rect(x,yb,bw,bd,fill=1)
            c.setFillColor(colors.black); c.setFont("Helvetica-Bold",16); c.drawCentredString(x+bw/2,yb+bd/2+2*mm,str(i+1))
            c.setFont("Helvetica",7); c.drawCentredString(x+bw/2,yb+bd/2-4*mm,"Allocated"); c.drawCentredString(x+bw/2,yb+6*mm,"2.40 x 4.80 m")
        else:
            c.setFillColor(colors.HexColor("#eeeeee")); c.rect(x,yb,bw,bd,fill=1); c.setFillColor(colors.black)
            c.saveState(); p=c.beginPath(); p.rect(x,yb,bw,bd); c.clipPath(p,stroke=0)
            c.setStrokeColor(colors.HexColor("#999999"))
            for k in range(-12,14): c.line(x+k*4*mm,yb,x+k*4*mm+bd,yb+bd)
            c.restoreState(); c.setStrokeColor(colors.black); c.rect(x,yb,bw,bd)
            c.setFillColor(colors.white); c.rect(x+1.5*mm,yb+bd/2-9*mm,bw-3*mm,20*mm,fill=1,stroke=0); c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold",16); c.drawCentredString(x+bw/2,yb+bd/2+4*mm,"6")
            c.setFont("Helvetica-Bold",6.5); c.drawCentredString(x+bw/2,yb+bd/2-1.5*mm,"BIN STORE &"); c.drawCentredString(x+bw/2,yb+bd/2-5.5*mm,"TURNING AREA")
    c.setFont("Helvetica",8); c.drawString(bx+4*mm,by+5*mm,"Gated vehicular access from A4 Upper Bristol Road  →")
    # legend
    lx,ly=bx,by-14*mm
    c.setFillColor(colors.HexColor("#fff6c9")); c.rect(lx,ly,6*mm,4*mm,fill=1); c.setFillColor(colors.black); c.setFont("Helvetica",8); c.drawString(lx+8*mm,ly+1*mm,"Allocated parking bay (5 no.)")
    c.setFillColor(colors.HexColor("#eeeeee")); c.rect(lx+65*mm,ly,6*mm,4*mm,fill=1); c.setFillColor(colors.black); c.drawString(lx+73*mm,ly+1*mm,"Bay 6: bin store and turning area, not available for parking")
    c.setFont("Helvetica-Bold",9); c.drawRightString(bx+BW,ly+1*mm,"Allocated parking bays: 5")
    footer(c,4,TOT); c.showPage()
    c.save()

def sh_finishes():
    c=new("st-huberts-close_schedule-of-finishes_chiltern-vale_2026-09.pdf","St Huberts Close - Schedule of Finishes, house types A-E (Rev C)","Chiltern Vale Developments Ltd (fictional)",
          "Fictional development-wide schedule of finishes for St Huberts Close, Gerrards Cross, Rev C Sept 2026. States all en-suites have walk-in showers (development scope) while the No. 59 brochure states a principal en-suite bathroom (unit scope). Plot schedule: No. 59 = type E (5 bed, standard spec); plots 53/57 = type D (4 bed, principal en-suite with bath).")
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
          ("2. Bathrooms and en-suites",[["Family bathroom","White suite with bath, thermostatic shower over bath and glass screen"],["En-suites","<b>All en-suites are fitted with walk-in showers with low-profile trays and glass screens.</b> Exception: house type D (see section 4)."],["Tiling","Full height to wet areas; half height elsewhere; porcelain floor tiles"],["Sanitaryware","Wall-hung WCs with concealed cisterns; chrome fittings throughout"]]),
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
    y=table(c,[["Type","Name","Bedrooms","Bathrooms (incl. en-suite)","Receptions","Garage","GIA sq ft"],["A","The Bulstrode","3","2","2","Single","1,420"],["B","The Chalfont","4","2","2","Single","1,760"],["C","The Denham","4","2","2","Double","2,098"],["D","The Fulmer","4","3","3","Double","2,512"],["E","The Hedgerley","5","3","5","Double","2,848"]],15*mm,y,[14*mm,34*mm,22*mm,40*mm,22*mm,20*mm,26*mm],hdr=colors.HexColor("#2e4a2e"),size=8.5,align_right_from=2)
    y-=6*mm
    y=table(c,[["Plot / No.","House type","Handed","Notes"],["51","C","No","—"],["53","D","Yes","Type D: principal en-suite with freestanding bath and separate shower"],["55","C","Yes","—"],["57","D","No","Type D: principal en-suite with freestanding bath and separate shower"],["59","E","No","Standard type E specification"],["61","E","Yes","—"]],15*mm,y,[24*mm,26*mm,20*mm,110*mm],hdr=colors.HexColor("#2e4a2e"),align_right_from=None,size=8.5)
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
if __name__=="__main__":
    for f in (kelso_survey,sh_finishes,sh_price): f()
    print("ok")
