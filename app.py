from flask import Flask,redirect,url_for,render_template,request,session,send_file
import json
from mail import send_email
import random
import os

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import io

app = Flask(__name__)
app.secret_key = 'atm55'


def generate_otp():
    return str(random.randint(100000,999999))



def get_data():
    with open('data.json','r') as file:
        data = json.load(file)
        return data

def update_data(data):
    with open('data.json','w') as file:
        json.dump(data,file,indent=4)
    

@app.route('/')
def base():
    return redirect('login')

@app.route('/login',methods = ['GET','POST'])
def login():
    info=request.args.get('info')
    if request.method == 'POST':
        email = request.form.get('email')
        pin = request.form.get('pin')
        data = get_data()
        users = data["users"]
        for i in users:
            if i["email"] == email and  i["pin"]==pin:
                session['username'] = i["username"]
                session['id'] = i["id"]
                return redirect(url_for('dashboard',user=session['username']))
        return redirect(url_for('login',info="Invalid login"))
    return render_template('login.html',info=info)


@app.route('/register',methods=['GET','POST'])
def register():
    info=request.args.get('info')
    if request.method == 'POST':
        username = request.form.get('uname')
        email = request.form.get('email')
        pin = request.form.get('pin')
        data = get_data()
        users = data["users"]

        for i in users:
            if i["email"] == email:
                return redirect(url_for('register',
                                       info="Email is already registered"))
     
        details = {
            "id": len(users)+1,
            "username":username,
            "email":email,
            "pin":pin,
            "history": [],
            "balance": 0
        }
        users.append(details)
        update_data(data)
        return redirect(url_for('login'))

    return render_template("register.html",info=info)

@app.route('/forgotpin',methods=['GET','POST'])
def forgotpin():
    info=request.args.get('info')
    if request.method == 'POST':
        email = request.form.get('email')
        data = get_data()
        users = data["users"]
        for i in users:
            if email == i["email"]:
                username = i["username"]
                otp = generate_otp()
                send_email(email,username,otp)
                session["otp"]=otp
                session['email']=email
                return redirect(url_for('verify'))
            
        return redirect('forgotpin',info="Email is not registered yet")

    return render_template('forgotpin.html',info=info)

@app.route('/verify',methods=['GET','POST'])
def verify():
    info=request.args.get('info')
    if request.method == 'POST':
        otp = request.form.get('otp')
        if otp == session["otp"]:
            session['otp']=None
            return redirect('resetpin')
        return redirect(url_for('verify',info="Invalid OTP"))
    
    return render_template('verify.html',info=info)

@app.route('/resetpin',methods=['GET','POST'])
def resetpin():
    info=request.args.get('info')
    if request.method == 'POST':
        npin = request.form.get('npin')
        cpin = request.form.get('cpin')
        if npin == cpin:
            data = get_data()
            users = data["users"]
            for i in users:
                if i["email"] == session['email']:
                    i["pin"] = npin
                    update_data(data)
                    return redirect(url_for('login'))

        return redirect(url_for('resetpin',info="Confirm the pin properly"))
    return render_template('resetpin.html',info=info)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('login')

@app.route('/dashboard/<user>')
def dashboard(user):
    if session.get('id'):
        return render_template("dashboard.html")
    return redirect(url_for('login'))

@app.route('/checkBalance')
def checkBalance():
    if session.get('id'):
        data=get_data()
        users = data["users"]
        for i in users:
            if i['id']==session['id']:
                balance=i['balance']
                return render_template('checkBalance.html', user=session["username"],balance=balance)        
    return redirect(url_for('logins'))    
@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if session.get('id'):
        info = request.args.get('info')

        if request.method == 'POST':
            try:
                amount = int(request.form.get('amount'))

                if amount <= 0:
                    raise ValueError

            except (ValueError, TypeError):
                return redirect(url_for(
                    'deposit',
                    info="Enter the proper amount"
                ))

            data = get_data()
            users = data["users"]

            for i in users:
                if i["id"] == session["id"]:
                    i["balance"] += amount
                    i["history"].append(f"{amount} deposited")

                    update_data(data)

                    return redirect(url_for('checkBalance'))

        return render_template("deposit.html", info=info)

    return redirect(url_for('login'))

@app.route('/withdraw',methods=['POST','GET'])
def withdraw():
    if session.get('id'):
        info=request.args.get('info')
        if request.method=='POST':
            try:
                amount = int(request.form.get('amount'))
                if amount < 0:
                    raise ValueError
            except(ValueError,TypeError):
                return redirect(url_for("withdraw",
                                info="Enter the proper amount"))
        
            data = get_data()
            users = data["users"]
            for i in users:
                if i["id"] == session["id"]:
                    if i["balance"]>=amount:
                        i["balance"]-=amount
                        i["history"].append(f"{amount} Withdraw")
                        update_data(data)
                        return redirect('checkbalance')
                    return redirect(url_for('withdraw',
                                info="Insufficent balance"))

        return render_template('withdraw.html',info=info)
    return redirect(url_for('login'))
            

@app.route('/viewtransactions')
def viewtransactions():
    if session.get('id'):
        data=get_data()
        users=data["users"]
        for i in users:
            if i["id"]==session["id"]:
                history=i["history"]
                lenght=len(history)
                return render_template("viewtransactions.html",
                               history=history,
                               lenght=lenght)
    return redirect(url_for('login'))

@app.route("/export_transactions_pdf")
def export_transactions_pdf():
    username = session["username"]
    data = get_data()
    users = data["users"]
    history = []
    for i in users:
        if i['id'] == session['id']:
            history = i['history']
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>ATM Transaction History</b>", styles["Title"]))
    elements.append(Paragraph(f"Customer : {username}", styles["Normal"]))
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))

    data = [["S.No","Transaction Details"]]

    for i, transaction in enumerate(history, start=1):
        data.append([str(i), transaction])

    table = Table(data, colWidths=[0.8*inch, 5.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),                  
    ]))
    elements.append(table)
    pdf.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{username}_transactions.pdf",
        mimetype="application/pdf"
    )

if __name__ == '__main__':
    app.run(debug=True)