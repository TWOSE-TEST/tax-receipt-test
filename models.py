from dataclasses import dataclass
import re
#from unittest import result
from flask import render_template_string #, make_response
import datetime
from webapp.extras.database import DB
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import datetime
#from webapp.views.process_receipts import delete_pdf
#import uuid
from xhtml2pdf import pisa
#import random
#import pdfkit


@dataclass
class constituent:
    """Represents a constituent object"""

    addressee: str
    position: str
    org_name: str
    address1: str
    address2: str
    address3: str
    address4: str
    address5: str
    city: str
    province: str
    postal_code: str
    country: str
    receipt_number: int
    receipt_amount: str
    gift_date: str
    fund_name: str
    gift_type: str
    benefit_amount: str
    email: str
    donor_rec_aurora: str
    donor_rec_other: str
    import_name: str
    import_date: str
    import_uuid: str
    temp_file: str
    pdf_copy: bool = False
    pdf_email: bool = False
    long_today: str = datetime.datetime.now().strftime("%B %d, %Y")
    year_issued: str = datetime.datetime.now().strftime("%Y")

    def check_address(self):
        if self.address1 == None or self.address1 == "":
            return f"{self.addressee} (Receipt Number: {self.receipt_number}) is missing their address.  Please correct the issue and reimport the CSV file."
        return None

    def check_email(self):
        pat = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-z]{1,3}$"
        email = self.email
        if not re.match(pat, email):
            return f"{self.addressee} (Receipt Number: {self.receipt_number}) email address is missing or not formatted correctly.  Please correct the issue and reimport the CSV file."
        return None

    def check_amount(self):
        amount = self.receipt_amount.replace(" ", "")
        amount = amount.replace("$", "")
        amount = amount.replace(",", "")
        if float(amount) > 25000:
            return f"{self.addressee} (Receipt Number: {self.receipt_number}) receipt amount is larger than $25,000.  Please correct the issue and reimport the CSV file."
        elif float(amount) < 20:
            return f"{self.addressee} (Receipt Number: {self.receipt_number}) receipt amount is less than $20.  Please correct the issue and reimport the CSV file. We do not receipt donations under $20."
        return None

    def check_date_format(self):
        success = True
        try:
            datetime.datetime.strptime(self.gift_date, '%Y-%m-%d')
        except:
            success = False
                
        if not success:
            return f"{self.addressee} - Date format is incorrect.  Date should be YYYY-MM-DD (ex. 2022-07-21)"
        
        return None

    def create_pdf(self):
        # https://xhtml2pdf.readthedocs.io/en/latest/usage.html#using-with-python-standalone
        # https://pythonprogramming.altervista.org/make-a-pdf-from-html-with-python-and-flask/?doing_wp_cron=1654025556.0902690887451171875000

        db = DB()
        sql = f"SELECT content FROM templates WHERE fund_type=%s;"
        d = db.select_w_values(sql, (self.fund_name,))
        if not d:
            sql = f"SELECT content FROM templates WHERE fund_type=%s;"
            d = db.select_w_values(sql, ("Default Template",))
        content = d[0][0]

        ### Process content
        with open("./pdf_template/pdf_template2.html", "r") as f:
            string = f.read()
            f.close()
            string = self.preprocess_html(string, content)

        constituent = self.__dict__

        # try:
        #     html = render_template_string(string, constituent=constituent)
        #     pdfkit.from_string(html, self.temp_file)
        # except ValueError as ve:
        #     print(ve)
        result_file = open("./pdf_temp/" + self.temp_file, "w+b")
        html = render_template_string(string, constituent=constituent, content=content)
        pisa_status = pisa.CreatePDF(html, dest=result_file, encoding='utf-8')
        # print(pisa_status)
        result_file.close()
        # print("====================================")

        return None

    def preprocess_html(self, html_txt, content):
        html_txt = html_txt.replace("[[ content ]]", content)
        html_txt = html_txt.replace("[[Addressee]]", "{{ constituent.addressee }}")
        html_txt = html_txt.replace("[[Donor Recognition Name]]", "{{ constituent.donor_rec_other }}")
        html_txt = html_txt.replace("[[Recognition Name Aurora]]", "{{ constituent.donor_rec_aurora }}")
        html_txt = html_txt.replace("[[Position]]", "{{ constituent.position }}")
        html_txt = html_txt.replace("[[Organization Name]]", "{{ constituent.org_name }}")
        html_txt = html_txt.replace("[[Address]]", "{{ constituent.address1 }}")
        html_txt = html_txt.replace("[[City]]", "{{ constituent.city }}")
        html_txt = html_txt.replace("[[Province]]", "{{ constituent.province }}")
        html_txt = html_txt.replace("[[Postal Code]]", "{{ constituent.postal_code }}")
        html_txt = html_txt.replace("[[Country]]", "{{ constituent.country }}")
        html_txt = html_txt.replace("[[Receipt Number]]", "{{ constituent.receipt_number }}")
        html_txt = html_txt.replace("[[Receipt Amount]]", "{{ constituent.receipt_amount }}")
        html_txt = html_txt.replace("[[Gift Date]]", "{{ constituent.gift_date }}")
        html_txt = html_txt.replace("[[Fund Description]]", "{{ constituent.fund_name }}")

        return html_txt

    def send_email(self):
        root_dir = os.getcwd() + "/pdf_temp/"
        attachment_location = root_dir + self.temp_file
        email_sender = "TaxReceipt@twose.ca"
        email_recipient = self.email

        ### Get email text from DB
        db = DB()
        sql = f"SELECT content FROM templates WHERE fund_type='Email Template';"
        d = db.select_rows(sql)


        msg = MIMEMultipart()
        msg["From"] = email_sender
        msg["To"] = email_recipient
        msg["Subject"] = "Edmonton Space & Science Foundation Tax Receipt (Do Not Reply)"
        msg.attach(
            MIMEText(f"{d[0][0]}", "html",)
        )

        filename = os.path.basename(attachment_location)
        attachment = open(attachment_location, "rb")
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment; filename= %s" % filename)
        msg.attach(part)

        try:
            server = smtplib.SMTP("smtp.office365.com", 587)
            server.ehlo()
            server.starttls()
            #test text
            server.login("TaxReceipt@twose.onmicrosoft.com", "Nat97615")
            text = msg.as_string()
            server.sendmail(email_sender, email_recipient, text)
            # print(f"Email was sent to {self.addressee}")
            server.quit()
            
            ### Delete PDF off of server
            os.remove(attachment_location)
        
        except Exception as e:
            print(f"SMTP server connection error.  The email was not sent: {e}")
            return False

        return True


    def check_columns(self):
        if self.addressee != "Addressee":
            e = "The Addressee column is missing or mislabeled in the csv file"
            return e
        if self.position != "Position":
            e = "The Position column is missing or mislabeled in the csv file"
            return e
        if self.org_name != "Organization Name":
            e = "The Organization Name column is missing or mislabeled in the csv file"
            return e
        if self.address1 != "Address line 1":
            e = "The Address line 1 column is missing or mislabeled in the csv file"
            return e
        if self.address2 != "Address line 2":
            e = "The Address line 2 column is missing or mislabeled in the csv file"
            return e
        if self.address3 != "Address line 3":
            e = "The Address line 3 column is missing or mislabeled in the csv file"
            return e
        if self.address4 != "Address line 4":
            e = "The Address line 4 column is missing or mislabeled in the csv file"
            return e
        if self.address5 != "Address line 5":
            e = "The Address line 5 column is missing or mislabeled in the csv file"
            return e
        if self.city != "City":
            e = "The City column is missing or mislabeled in the csv file"
            return e
        if self.province != "Province":
            e = "The Province column is missing or mislabeled in the csv file"
            return e
        if self.postal_code != "Postal Code":
            e = "The Postal Code column is missing or mislabeled in the csv file"
            return e
        if self.country != "Country":
            e = "The Country column is missing or mislabeled in the csv file"
            return e
        if self.receipt_number != "Receipt Number":
            e = "The Receipt Number column is missing or mislabeled in the csv file"
            return e
        if self.receipt_amount != "Receipt amount":
            e = "The Receipt amount column is missing or mislabeled in the csv file"
            return e
        if self.gift_date != "Gift date":
            e = "The Gift date amount column is missing or mislabeled in the csv file"
            return e
        if self.fund_name != "Fund description_1":
            e = "The Fund description_1 amount column is missing or mislabeled in the csv file"
            return e
        if self.gift_type != "Gift type":
            e = "The Gift type column is missing or mislabeled in the csv file"
            return e
        if self.benefit_amount != "Benefits Amount (Total For Gift)":
            e = "The Benefits Amount (Total For Gift) column is missing or mislabeled in the csv file"
            return e
        if self.email != "Phone number":
            e = "The Phone number column is missing or mislabeled in the csv file"
            return e
        if self.donor_rec_aurora != "Donor Recognition Aurora_1":
            e = "The Donor Recognition Aurora_1 column is missing or mislabeled in the csv file"
            return e
        if self.donor_rec_other != "Donor Recognition Name_1":
            e = "The Donor Recognition Name_1 column is missing or mislabeled in the csv file"
            return e
        return None
