"""Generate PDF test files that look like real PE board pack financial reports."""
from fpdf import FPDF


def create_pl_pdf():
    """P&L that looks like a management accounts board pack page."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Meridian Software Inc.", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Monthly Profit & Loss Statement", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "For the Period Ending March 2026", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Prepared for Board of Directors", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Table
    headers = ["Month", "Revenue", "COGS", "Gross Profit", "S&M", "R&D", "G&A", "Total OpEx", "EBITDA"]
    data = [
        ["Oct-25", "$2,859,000", "$743,340", "$2,115,660", "$1,000,650", "$514,620", "$343,080", "$1,858,350", "$257,310"],
        ["Nov-25", "$2,973,000", "$772,980", "$2,200,020", "$1,040,550", "$535,140", "$356,760", "$1,932,450", "$267,570"],
        ["Dec-25", "$3,092,000", "$803,920", "$2,288,080", "$1,082,200", "$556,560", "$370,680", "$2,009,440", "$278,640"],
        ["Jan-26", "$3,216,000", "$835,360", "$2,380,640", "$1,125,600", "$578,880", "$385,440", "$2,089,920", "$290,720"],
        ["Feb-26", "$3,100,000", "$837,000", "$2,263,000", "$1,116,000", "$561,800", "$378,200", "$2,056,000", "$207,000"],
        ["Mar-26", "$3,400,000", "$901,000", "$2,499,000", "$1,190,000", "$618,000", "$402,000", "$2,210,000", "$289,000"],
    ]

    col_widths = [18, 22, 22, 24, 22, 20, 20, 22, 22]

    # Header row
    pdf.set_font("Helvetica", "B", 7)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, h, border=1, align="C")
    pdf.ln()

    # Data rows
    pdf.set_font("Helvetica", "", 7)
    for row in data:
        for i, val in enumerate(row):
            pdf.cell(col_widths[i], 6, val, border=1, align="R" if i > 0 else "C")
        pdf.ln()

    # Total row
    pdf.set_font("Helvetica", "B", 7)
    total = ["TOTAL", "$18,640,000", "$4,893,600", "$13,746,400", "$6,555,000", "$3,365,000", "$2,236,160", "$12,156,160", "$1,590,240"]
    for i, val in enumerate(total):
        pdf.cell(col_widths[i], 7, val, border=1, align="R" if i > 0 else "C")
    pdf.ln()

    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "* Feb-26 revenue dip due to delayed enterprise contract close", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "* Mar-26 reflects recovery with new logos contributing $180K", new_x="LMARGIN", new_y="NEXT")

    pdf.output("data/test/pl_board_pack.pdf")
    print("Created pl_board_pack.pdf")


def create_balance_sheet_pdf():
    """Balance sheet formatted like a QoE report page."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Balance Sheet Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, "Meridian Software Inc. - As of March 31, 2026", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    headers = ["", "Dec-25", "Jan-26", "Feb-26", "Mar-26"]
    col_w = [45, 28, 28, 28, 28]

    sections = [
        ("ASSETS", None),
        ("Cash & Equivalents", ["5,200,000", "5,450,000", "5,100,000", "5,600,000"]),
        ("Accounts Receivable", ["3,800,000", "4,100,000", "3,900,000", "4,300,000"]),
        ("Prepaid Expenses", ["320,000", "340,000", "330,000", "350,000"]),
        ("Total Current Assets", ["9,320,000", "9,890,000", "9,330,000", "10,250,000"]),
        ("PP&E, Net", ["1,800,000", "1,750,000", "1,700,000", "1,650,000"]),
        ("Intangible Assets", ["4,200,000", "4,150,000", "4,100,000", "4,050,000"]),
        ("Total Assets", ["15,320,000", "15,790,000", "15,130,000", "15,950,000"]),
        ("", None),
        ("LIABILITIES & EQUITY", None),
        ("Accounts Payable", ["1,100,000", "1,200,000", "1,150,000", "1,250,000"]),
        ("Accrued Liabilities", ["850,000", "900,000", "870,000", "920,000"]),
        ("Total Current Liabilities", ["1,950,000", "2,100,000", "2,020,000", "2,170,000"]),
        ("Long-Term Debt", ["3,500,000", "3,400,000", "3,300,000", "3,200,000"]),
        ("Total Liabilities", ["5,450,000", "5,500,000", "5,320,000", "5,370,000"]),
        ("Total Equity", ["9,870,000", "10,290,000", "9,810,000", "10,580,000"]),
        ("Total Liabilities & Equity", ["15,320,000", "15,790,000", "15,130,000", "15,950,000"]),
    ]

    # Header
    pdf.set_font("Helvetica", "B", 8)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, align="C")
    pdf.ln()

    for label, vals in sections:
        if vals is None:
            # Section header or blank
            pdf.set_font("Helvetica", "B", 8)
            if label:
                pdf.cell(sum(col_w), 7, label, border=0)
                pdf.ln()
            else:
                pdf.ln(3)
            continue

        is_total = label.startswith("Total")
        pdf.set_font("Helvetica", "B" if is_total else "", 8)
        pdf.cell(col_w[0], 6, label, border=1 if is_total else 0)
        for i, v in enumerate(vals):
            pdf.cell(col_w[i + 1], 6, v, border=1 if is_total else 0, align="R")
        pdf.ln()

    pdf.output("data/test/balance_sheet_report.pdf")
    print("Created balance_sheet_report.pdf")


if __name__ == "__main__":
    create_pl_pdf()
    create_balance_sheet_pdf()
    print("\nAll PDF test files created.")
