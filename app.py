import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import random
import string
import qrcode
import io
import base64
from babel.dates import format_date
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = 'secreto'

# Conexão com banco de dados
def init_db():
    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            email TEXT NOT NULL,
            tipo_reserva TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            data TEXT NOT NULL,
            hora TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            senha TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Gerar um código de reserva alfanumérico de 6 dígitos
def gerar_codigo_reserva():
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choices(caracteres, k=6))

# Função para adicionar o evento no Google Calendar
def adicionar_evento_google_calendar(reserva_info):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'credentials.json'

    # Carregar as credenciais do serviço
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)

    # Definir os detalhes do evento
    evento = {
        'summary': f'Reserva - {reserva_info["nome"]}',
        'location': 'Lakes Shopping - Av. Saquarema, 567 - Centro, Saquarema - RJ, 28990-000, Brasil',
        'description': f'Reserva para {reserva_info["pessoas"]} pessoas.',
        'start': {
            'dateTime': f'{reserva_info["data"]}T{reserva_info["hora"]}:00',
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': f'{reserva_info["data"]}T{int(reserva_info["hora"][:2]) + 1}:{reserva_info["hora"][3:]}:00',
            'timeZone': 'America/Sao_Paulo',
        }
    }

    # Inserir o evento no Google Calendar
    event = service.events().insert(calendarId='reservaselpatron@gmail.com', body=evento).execute()
    print("Evento criado com sucesso:", event.get("htmlLink"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/reservar', methods=['GET', 'POST'])
def reservar():
    if request.method == 'POST':
        nome = request.form['nome']
        whatsapp = request.form['whatsapp']
        email = request.form['email']
        tipo_reserva = request.form['tipo_reserva']
        quantidade = request.form['quantidade']
        data = request.form['data']
        hora = request.form['hora']

        # Gerar um código de reserva alfanumérico
        codigo_reserva = gerar_codigo_reserva()

        conn = sqlite3.connect('reservas.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reservas (nome, whatsapp, email, tipo_reserva, quantidade, data, hora)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, whatsapp, email, tipo_reserva, quantidade, data, hora))
        conn.commit()
        conn.close()

        # Gerar QR Code com as informações da reserva
        qr_data = f'Reserva: {codigo_reserva}\nNome: {nome}\nPessoas: {quantidade}\nData: {data}\nHora: {hora}'
        qr_image = qrcode.make(qr_data)
        buffered = io.BytesIO()
        qr_image.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Preparar informações da reserva
        reserva_info = {
            'nome': nome,
            'pessoas': quantidade,
            'data': data,
            'hora': hora,
            'codigo_reserva': codigo_reserva
        }

        # Enviar e-mail de confirmação para o cliente
        enviar_email_cliente(email, nome, reserva_info, qr_code_base64)

        # Enviar e-mail de notificação para o restaurante
        enviar_email_restaurante(reserva_info)

        # Adicionar evento no Google Calendar
        adicionar_evento_google_calendar(reserva_info)

        flash('Reserva feita com sucesso! Um e-mail foi enviado com os detalhes da sua reserva.')
        return redirect(url_for('sucesso', nome=nome, codigo=codigo_reserva, data_reserva=data))

    return render_template('reservas.html')

def enviar_email_cliente(email, nome, reserva_info, qr_code_base64):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    login_email = 'reservaselpatron@gmail.com'
    app_password = 'kkqobpebaxrzpqwz'  # Insira sua senha de aplicativo do Gmail

    msg = MIMEMultipart()
    msg['From'] = login_email
    msg['To'] = email
    msg['Subject'] = f'Confirmação de Reserva - El Patron | Código: {reserva_info["codigo_reserva"]}'

    body = f'''
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Olá {nome},</h2>
            <p>Sua reserva foi feita com sucesso!</p>
            <p><strong>Código da reserva:</strong> {reserva_info["codigo_reserva"]}</p>
            <p><strong>Detalhes da sua reserva:</strong></p>
            <ul>
                <li><strong>Nome:</strong> {nome}</li>
                <li><strong>Número de pessoas:</strong> {reserva_info["pessoas"]}</li>
                <li><strong>Data e Hora:</strong> {reserva_info["data"]} às {reserva_info["hora"]}</li>
            </ul>
            <p>Endereço: Lakes Shopping - Av. Saquarema, 567 - Centro, Saquarema - RJ, 28990-000, Brasil.</p>
            <p>Nosso endereço no Google Maps: <a href="https://g.co/kgs/VfsmiPf" target="_blank">Clique aqui</a></p>
            <p>Por favor, chegue no horário e, caso precise cancelar ou alterar sua reserva, entre em contato conosco: <a href="https://wa.me/5521980375523">(22) 98130-4308</a></p>
            <p>Apresente este QRCode ao chegar no restaurante:</p>
            <img src="data:image/png;base64,{qr_code_base64}" alt="QR Code da Reserva"/>
            <p>Até breve!</p>
        </body>
    </html>
    '''
    msg.attach(MIMEText(body, 'html'))

    # Conectar ao servidor SMTP e enviar o e-mail
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(login_email, app_password)
    server.sendmail(login_email, email, msg.as_string())
    server.quit()

def enviar_email_restaurante(reserva_info):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    login_email = 'reservaselpatron@gmail.com'
    app_password = 'kkqobpebaxrzpqwz'

    data_reserva_obj = datetime.strptime(reserva_info['data'], '%Y-%m-%d')
    dia_semana = format_date(data_reserva_obj, 'EEEE', locale='pt_BR')

    mensagem_personalizada = f"Olá El Patrón, você tem uma nova reserva para {dia_semana}, {reserva_info['data']}."

    msg = MIMEMultipart()
    msg['From'] = login_email
    msg['To'] = 'reservaselpatron@gmail.com'
    msg['Subject'] = f'Nova Reserva - {reserva_info["codigo_reserva"]}'

    body = f'''
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>{mensagem_personalizada}</h2>
            <p><strong>Detalhes da reserva:</strong></p>
            <ul>
                <li><strong>Nome:</strong> {reserva_info['nome']}</li>
                <li><strong>Número de pessoas:</strong> {reserva_info['pessoas']}</li>
                <li><strong>Data e Hora:</strong> {reserva_info['data']} às {reserva_info['hora']}</li>
                <li><strong>Código da Reserva:</strong> {reserva_info["codigo_reserva"]}</li>
            </ul>
            <p>Por favor, confirme a reserva o mais rápido possível.</p>
        </body>
    </html>
    '''
    msg.attach(MIMEText(body, 'html'))

    # Conectar ao servidor SMTP e enviar o e-mail
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(login_email, app_password)
    server.sendmail(login_email, 'reservaselpatron@gmail.com', msg.as_string())
    server.quit()

@app.route('/sucesso/<nome>/<codigo>/<data_reserva>')
def sucesso(nome, codigo, data_reserva):
    return render_template('sucesso.html', nome=nome, codigo=codigo, data_reserva=data_reserva)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        conn = sqlite3.connect('reservas.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario_id'] = usuario[0]
            session['usuario_nome'] = usuario[1]
            return redirect(url_for('admin'))
        else:
            flash('E-mail ou senha incorretos! Tente novamente.')

    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))  # Esta linha agora está corretamente indentada

    conn = sqlite3.connect('reservas.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reservas')
    reservas = cursor.fetchall()
    conn.close()

    return render_template('admin.html', reservas=reservas)


@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    session.pop('usuario_nome', None)
    return redirect(url_for('login'))

@app.route('/cadastrar_usuario', methods=['GET', 'POST'])
def cadastrar_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        
        conn = sqlite3.connect('reservas.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)', (nome, email, senha))
        conn.commit()
        conn.close()
        
        flash('Usuário cadastrado com sucesso!')
        return redirect(url_for('login'))

    return render_template('cadastrar_usuario.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
