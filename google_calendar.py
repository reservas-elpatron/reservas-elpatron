import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Carregar as credenciais do arquivo JSON
def load_credentials():
    credentials = service_account.Credentials.from_service_account_file(
        'credentials.json',
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    return credentials

# Função para adicionar uma reserva ao Google Calendar
def add_reservation_to_calendar(name, date, time, people_count):
    # Configurações do Google Calendar
    calendar_id = 'reservaselpatron@gmail.com'  # Substitua pelo seu ID de calendário, se não for o primário

    # Carregar credenciais
    credentials = load_credentials()
    service = build('calendar', 'v3', credentials=credentials)

    # Configurar dados do evento
    event = {
        'summary': f'Reserva para {name}',
        'description': f'Reserva feita para {people_count} pessoas.',
        'start': {
            'dateTime': f'{date}T{time}:00',
            'timeZone': 'Europe/Lisbon',  # Ajuste para o fuso horário do restaurante
        },
        'end': {
            'dateTime': f'{date}T{time}:00',
            'timeZone': 'Europe/Lisbon',
        },
    }

    # Inserir evento no Google Calendar
    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"Reserva adicionada com sucesso ao Google Calendar: {event.get('htmlLink')}")

# Teste da função
# add_reservation_to_calendar("João Silva", "2024-10-15", "18:30", 4)
