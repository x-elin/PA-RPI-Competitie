import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from w1thermsensor import W1ThermSensor, Unit
import RPi.GPIO as GPIO

host_name = '192.168.178.81'  # IP-adres van de Raspberry Pi
host_port = 8000

# Variabelen voor temperatuurregeling
RELAIS_PINS = [17, 18, 19]  # GPIO-pinnen voor relais -> ltr veranderen
SENSOR_NAMEN = ['vak 1', 'vak 2', 'vak 3']  # Namen van de vakken
DOELTEMPERATUREN = [7, 8, 9]  # Doeltemperaturen voor elk vak
HYSTERESIS = 1  # Hysteresis waarde: verschil tussen in- en uitschakelen van relays

# GPIO-pinnen voor de magnetische contactschakelaars
MAGNET_PINS = [23, 24, 25,]  # GPIO-pinnen voor de magnetische contactschakelaars -> ltr veranderen

# Variabelen voor het bijhouden van de tijd sinds elk vak open was
tijd_laatst_geopend = [None] * len(SENSOR_NAMEN)

# GPIO-initialisatie
GPIO.setmode(GPIO.BCM)
for pin in RELAIS_PINS:
    GPIO.setup(pin, GPIO.OUT)

for pin in MAGNET_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Main code voor temperatuursensoren en relais
def getTemperature():
    temperatures = []
    for sensor in W1ThermSensor.get_available_sensors():
        temp = sensor.get_temperature(Unit.DEGREES_C)
        temperatures.append(temp)
    return temperatures

def controle_relais(sensor_index, temp):
    doeltemperatuur = DOELTEMPERATUREN[sensor_index]
    relay_pin = RELAIS_PINS[sensor_index]

    if temp < doeltemperatuur - HYSTERESIS:
        GPIO.output(relay_pin, GPIO.HIGH)
    elif temp > doeltemperatuur + HYSTERESIS:
        GPIO.output(relay_pin, GPIO.LOW)

# Main code voor de webpagina
class MyServer(BaseHTTPRequestHandler):

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _redirect(self, path):
        self.send_response(303)
        self.send_header('Content-type', 'text/html')
        self.send_header('Location', path)
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self._set_doeltemperaturen()
            self.krijg_status()
            return
        if self.path == "/set":
            self._set_doeltemperaturen()
            return

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("utf-8")
        post_data = json.loads(post_data)

        # Update de doeltemperaturen met de waarden vanuit het formulier
        for i, doeltemp in enumerate(post_data["doeltemperaturen"]):
            DOELTEMPERATUREN[i] = int(doeltemp)

        # Stuur een redirect om de pagina te vernieuwen met de nieuwe/bijgewerkte doeltemperaturen
        self._redirect('/')

    def krijg_status(self):
        global tijd_laatst_geopend
        temperatures = getTemperature()
        status_html = ""
        for i, temp in enumerate(temperatures):
            relais_status = GPIO.input(RELAIS_PINS[i])
            status_html += f"<p>{SENSOR_NAMEN[i]}: Temperature: {temp}C, Status: {'On' if relais_status else 'Off'}"
            
            # Controleer de status van de magnetische contactschakelaar voor dit vak
            if GPIO.input(MAGNET_PINS[i]) == GPIO.LOW:
                if tijd_laatst_geopend[i] is None:
                    tijd_laatst_geopend[i] = time.time()
                tijd_sinds_laatst_geopend = time.time() - tijd_laatst_geopend[i]
                status_html += f", Vak open: {tijd_sinds_laatst_geopend:.2f} seconden geleden"
            else:
                tijd_laatst_geopend[i] = None
            
            status_html += "</p>"

        html = f'''
           <!DOCTYPE html>
           <html lang="en">
           <head>
               <meta charset="UTF-8">
               <meta name="viewport" content="width=device-width, initial-scale=1.0">
               <title>Thermaguard</title>
               <style>
                   /* Algemeen */
                   body {{
                       font-family: monospace; /* Monospace lettertype voor de hele pagina */
                   }}

                   /* Achtergrond en tekstkleuren */
                   .background-light {{
                       background-color: #b3cde0; /* Lichte tint achtergrond */
                       color: #011f4b; /* Donkere tint voor letters */
                   }}

                   /* Labels */
                   .label {{
                       color: #011f4b; /* Donkere tint voor labels */
                       font-family: monospace; /* Monospace lettertype voor labels */
                   }}

                   /* Invoervelden */
                   .input {{
                       background-color: #b3cde0; /* Lichte tint achtergrond voor invoervelden */
                       color: #011f4b; /* Donkere tint voor invoertekst */
                       border: 1px solid #011f4b; /* Randkleur invoervelden */
                       border-radius: 4px; /* Afgeronde randen voor invoervelden */
                       padding: 8px; /* Ruimte binnenin invoervelden */
                       font-family: monospace; /* Monospace lettertype voor invoervelden */
                   }}

                   /* Knoppen */
                   .button {{
                       background-color: #03396c; /* Donkere tint achtergrond voor knop */
                       color: #b3cde0; /* Lichte tint voor knoptekst */
                       border: none; /* Geen rand voor knop */
                       border-radius: 4px; /* Afgeronde randen voor knop */
                       padding: 10px 20px; /* Ruimte binnenin knop */
                       cursor: pointer; /* Verander cursor naar wijzervorm bij zweven */
                       transition: background-color 0.3s ease; /* Soepele overgang voor achtergrondkleur */
                       font-family: monospace; /* Monospace lettertype voor knoppen */
                   }}

                   /* Hoofdtekst */
                   .heading {{
                       color: #005b96; /* Middentint voor hoofdtekst */
                       font-family: monospace; /* Monospace lettertype voor hoofdtekst */
                   }}

                   /* Hover-effect voor knoppen */
                   .button:hover {{
                       background-color: #005b96; /* Verander achtergrondkleur bij zweven */
                       color: #b3cde0; /* Behoud lichte tint voor tekst */
                   }}

                   /* Actieve staat voor knoppen */
                   .button:active {{
                       background-color: #6497b1; /* Verander achtergrondkleur bij klikken */
                       font-family: monospace; /* Monospace lettertype voor actieve knoppen */
                   }}

                   /* Weergave laatst geopende status */
                   .status {{
                       margin-top: 20px; /* Ruimte boven laatst geopende status */
                       font-family: monospace; /* Monospace lettertype voor laatst geopende status */
                   }}
               </style>
               <script>
                   document.getElementById("temperatureForm").addEventListener("submit", function(event) {{
                       event.preventDefault();

                       // Verzamel doeltemperaturen voor elk vak
                       var goalTemperatures = {{
                           1: parseFloat(document.getElementById("slot1").value),
                           2: parseFloat(document.getElementById("slot2").value),
                           3: parseFloat(document.getElementById("slot3").value),
                       }};

                       // Stuur doeltemperaturen naar de backend
                       fetch('/set_goal_temperatures', {{
                           method: 'POST', 
                           headers: {{
                               'Content-Type': 'application/json',
                           }},
                           body: JSON.stringify(goalTemperatures)
                       }})
                       .then(response => {{
                           if (!response.ok) {{
                               throw new Error('Niet mogelijk om doeltemperatuur in te stellen');
                           }}
                           return response.json();
                       }})
                       .then(data => {{
                           console.log('Goal temperatures set successfully:', data);
                       }})
                       .catch(error => {{
                           console.error('Error setting goal temperatures:', error);
                       }});
                   }});
               </script>
           </head>
           <body class="background-light">
               <h1 class="heading">Thermaguard</h1>
               <form id="temperatureForm">
                   <label for="slot1" class="label">Doeltemperatuur voor vak 1:</label>
                   <input type="number" id="slot1" name="slot1" class="input" min="0" max="100" step="0.1" required><br><br>

                   <label for="slot2" class="label">Doeltemperatuur voor vak 2:</label>
                   <input type="number" id="slot2" name="slot2" class="input" min="0" max="100" step="0.1" required><br><br>

                   <label for="slot3" class="label">Doeltemperatuur voor vak 3:</label>
                   <input type="number" id="slot3" name="slot3" class="input" min="0" max="100" step="0.1" required><br><br>
                 <button type="submit" class="button">Opslaan</button>
               </form>
               <div class="status">
                   <h2 class="heading">Laatst geopend:</h2>
                   {self._get_last_opened_status()}
               </div> 
           </body>
           </html>
        '''
        self.do_HEAD()
        self.wfile.write(html.encode("utf-8"))

    def _set_doeltemperaturen(self):
        self.krijg_status()

    def _get_last_opened_status(self):
        status_html = ""
        for i, time_opened in enumerate(tijd_laatst_geopend):
            if time_opened is not None:
                status_html += f"<p>{SENSOR_NAMEN[i]}: Vak open: {time.time() - time_opened:.2f} seconden geleden</p>"
            else:
                status_html += f"<p>{SENSOR_NAMEN[i]}: Niet geopend</p>"
        return status_html

if __name__ == '__main__':
    http_server = HTTPServer((host_name, host_port), MyServer)
    print("Server Starts - %s:%s" % (host_name, host_port))
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()
