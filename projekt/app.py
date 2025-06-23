import mysql.connector, secrets
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, render_template, request, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

from dotenv import load_dotenv
load_dotenv()


import os
connection = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER', 'user'),
    password=os.getenv('DB_PASSWORD', 'password'),
    database=os.getenv('DB_NAME', 'mydatabase')
)


# strona startowa 1
@app.route('/')
def startPage():
    # Sprawdzenie czy użytkownik jest zalogowany
    if 'logged_in' in session and session['logged_in']:
        # Przekierowanie na homePage, jeśli jest zalogowany 
        return redirect(url_for('homePage'))
    error = False
    success = request.args.get('success')  
    # Jeśli nie jest zalogowany to przekierowanie na startPage
    return render_template("startPage.html", error=error, success=success)
   

# strona z formularzem logowania 2.1
@app.route('/logIn', methods=['GET', 'POST'])
def logIn():
    # Dane z formularza logowania
    password = request.form.get("password")
    email = request.form.get("email")

    # Sprawdzanie poprawności danych logowania
    cursor = connection.cursor()
    sql = "SELECT * FROM Users WHERE email = %s AND password = %s"
    val = (email, password)
    cursor.execute(sql, val)
    user = cursor.fetchone()
    cursor.close()

    if user:
        # Jeśli użytkownik jest poprawnie zalogowany, zapisanie informacji o zalogowaniu do sesji 
        session['logged_in'] = True
        session['email'] = email
        return redirect(url_for('homePage'))
    else:
        # Błąd logowania
        error = True
        return render_template("logIn.html", error=error)

# wylogowanie
@app.route('/logOut', methods=['POST'])
def logOut():
    # Usunięcie informacji o zalogowaniu z sesji
    session.pop('logged_in', None)
    session.pop('email', None)
    return redirect(url_for('logIn'))


# strona z formularzem rejestracji 2.2
@app.route('/register',  methods=['GET', 'POST'])
def register():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('homePage'))
    if request.method == 'POST':
       
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")
        password2 = request.form.get("password2")
        registration = request.form.get("registration")

        if password != password2:
            error = "Hasła nie pasują do siebie."
            return render_template("register.html", error=error)

        # Sprawdzanie istnienia użytkownika w bazie danych
        cursor = connection.cursor()
        sql = "SELECT * FROM Users WHERE email = %s"
        val = (email,)
        cursor.execute(sql, val)
        user = cursor.fetchone()

        if user:
            # Użytkownik o podanej nazwie już istnieje
            error = True
            return render_template("register.html", error=error)

       # Dodaj nowego użytkownika do bazy danych
        sql = "INSERT INTO Users (name, email, password, registration, score) VALUES (%s, %s, %s, %s, %s)"
        val = (name, email, password, registration, 0)
        cursor.execute(sql, val)
        connection.commit()
       
        # Pobierz userID nowo zarejestrowanego użytkownika
        sql = "SELECT userID FROM Users WHERE email = %s"
        val = (email,)
        cursor.execute(sql, val)
        user = cursor.fetchone()
        
        if user:
            userID = user[0]  # Pobierz userID z pierwszego elementu krotki

            # Dodaj nowy samochód do bazy Vehicle
            sql = "INSERT INTO Vehicle (userID, vehicleName, registration) VALUES (%s, %s, %s)"
            val = (userID, "moj samochod", registration)
            cursor.execute(sql, val)
            connection.commit()

        session['logged_in'] = True
        session['email'] = email

        cursor.close()
        
        # Przekierowanie do strony głownej po pomyślnej rejestracji
        return redirect(url_for('homePage', success=True))
    
    return render_template("register.html")

# strona główna 3
@app.route('/homePage')
def homePage():
    return render_template("homePage.html")

# regulamin 4.1
@app.route('/rules')
def rules():
    with open('static/regulamin.txt', 'r', encoding='utf-8') as file:
        content = file.read()
    return render_template('rules.html', content=content)


# profil 4.2
@app.route('/userProfile')
def userProfile():
    # Sprawdź, czy użytkownik jest zalogowany
    if 'logged_in' in session and session['logged_in']:
        email = session['email']

       # Pobierz dane użytkownika z bazy danych na podstawie emaila
        cursor = connection.cursor()
        sql_user = "SELECT userID, name FROM Users WHERE email = %s"
        val_user = (email,)
        cursor.execute(sql_user, val_user)
        user_data = cursor.fetchone()

        # Sprawdź, czy dane użytkownika zostały znalezione w bazie danych
        if user_data:
            # Pobierz pojazdy związane z userID
            userID = user_data[0]
            name = user_data[1]

            sql_vehicles = "SELECT * FROM Vehicle WHERE userID = %s"
            val_vehicles = (userID,)
            cursor.execute(sql_vehicles, val_vehicles)
            vehicles = cursor.fetchall()
            cursor.close()

            # Przekazanie danych pojazdów do szablonu
            return render_template("userProfile.html", vehicles=vehicles, name=name, email=email) 

    else:
        # Jeśli użytkownik nie jest zalogowany, przekieruj go do strony logowania
        return redirect(url_for('logIn'))

# edycja nazwy pojazdów (dodatkowe)
@app.route('/editVehicle/<int:vehicleID>', methods=['POST'])
def editVehicle(vehicleID):
    if 'logged_in' in session and session['logged_in']:
        new_vehicle_name = request.form.get(f"new_vehicle_name_{vehicleID}")

        if new_vehicle_name:
            try:
                cursor = connection.cursor()
                sql = "UPDATE Vehicle SET vehicleName = %s WHERE vehicleID = %s"
                val = (new_vehicle_name, vehicleID)
                cursor.execute(sql, val)
                connection.commit()
                cursor.close()
                flash('Vehicle name updated successfully', 'success')
            except Exception as e:
                flash(f'Error updating vehicle name: {str(e)}', 'error')
        else:
            flash('New vehicle name cannot be empty', 'error')

        return redirect(url_for('userProfile'))
    else:
        return redirect(url_for('logIn'))

# dodanie nowego pojazdu (dodatkowe)
@app.route('/addVehicle', methods=['GET', 'POST'])
def addVehicle():
    if 'logged_in' in session and session['logged_in']:
        email = session['email']
        new_vehicle_name = request.form.get("new_vehicle_name")
        new_vehicle_registration = request.form.get("new_vehicle_registration")

        cursor = connection.cursor()
        sql_user = "SELECT userID FROM Users WHERE email = %s"
        val_user = (email,)
        cursor.execute(sql_user, val_user)
        user_data = cursor.fetchone()

        if user_data:
            userID = user_data[0]

            sql = "INSERT INTO Vehicle (userID, vehicleName, registration) VALUES (%s, %s, %s)"
            val = (userID, new_vehicle_name, new_vehicle_registration)
            cursor.execute(sql, val)
            connection.commit()
            cursor.close()

        return redirect(url_for('userProfile'))
    else:
        return redirect(url_for('logIn'))

# historia 5.1
@app.route('/userHistory')
def userHistory():
    # Sprawdź, czy użytkownik jest zalogowany
    if 'logged_in' in session and session['logged_in']:
        email = session['email']

        # Pobierz userID na podstawie adresu email
        cursor = connection.cursor()
        sql_user = "SELECT userID FROM Users WHERE email = %s"
        val_user = (email,)
        cursor.execute(sql_user, val_user)
        user_result = cursor.fetchone()

        if user_result:
            userID = user_result[0]

            # Pobierz historię rezerwacji dla danego użytkownika
            sql_reservations = "SELECT * FROM Reservations WHERE userID = %s"
            val_reservations = (userID,)
            cursor.execute(sql_reservations, val_reservations)
            reservations = cursor.fetchall()
            cursor.close()

            return render_template("userHistory.html", reservations=reservations)
    else:
        # Obsługa przypadku, gdy użytkownik nie jest zalogowany
        return render_template("login.html", error="Proszę się zalogować, aby zobaczyć historię rezerwacji.")

# nagrody 4.3
@app.route('/userAwards')
def userAwards():
    # Sprawdź, czy użytkownik jest zalogowany
    if 'logged_in' in session and session['logged_in']:
        email = session['email']

        # Pobierz liczbę punktów (score) z bazy danych
        cursor = connection.cursor()
        sql_user_score = "SELECT score FROM Users WHERE email = %s"
        val_user_score = (email,)
        cursor.execute(sql_user_score, val_user_score)
        user_score = cursor.fetchone()[0]  # Pobierz pierwszą kolumnę wyniku zapytania
        cursor.close()

        return render_template("userAwards.html", user_score=user_score)
    else:
        # Jeśli użytkownik nie jest zalogowany, przekieruj go do strony logowania
        return redirect(url_for('logIn'))


# rezerwacja 4.4
@app.route('/booking', methods=['GET', 'POST'])
def booking():
    # Pobierz pojazdy zawsze, niezależnie od tego, czy formularz został przesłany czy nie
    if 'logged_in' in session and session['logged_in']:
        email = session['email']

        # Pobierz dane użytkownika z bazy danych na podstawie emaila
        cursor = connection.cursor()
        sql_user = "SELECT userID, name FROM Users WHERE email = %s"
        val_user = (email,)
        cursor.execute(sql_user, val_user)
        user_data = cursor.fetchone()

        sql_parking = "SELECT * FROM Parking"
        cursor.execute(sql_parking)
        parkings = cursor.fetchall()

        # Sprawdź, czy dane użytkownika zostały znalezione w bazie danych
        if user_data:
            # Pobierz pojazdy związane z userID
            userID = user_data[0]

            sql_vehicles = "SELECT * FROM Vehicle WHERE userID = %s"
            val_vehicles = (userID,)
            cursor.execute(sql_vehicles, val_vehicles)
            vehicles = cursor.fetchall()
            cursor.close()
            # Przekazanie danych do szablonu HTML

            if request.method == 'POST':
                # Pobierz dane z formularza
                vehicle = request.form['vehicle']
                parking_name = request.form['parking']
                arrival_time_str = request.form['arrival_time']
                duration_hours = int(request.form['duration_hours'])
                duration_minutes = int(request.form['duration_minutes'])
                space_type = request.form['space_type']


                # Konwertuj datę przyjazdu na obiekt datetime
                arrival_time = datetime.strptime(arrival_time_str, '%Y-%m-%dT%H:%M')

                # Oddziel datę od godziny
                arrival_date = arrival_time.date()
                arrival_hour = arrival_time.time()

                # Dodaj czas postoju do godziny przyjazdu, aby uzyskać godzinę wyjazdu
                departure_time = (datetime.combine(arrival_date, arrival_hour) +
                                  timedelta(hours=duration_hours, minutes=duration_minutes)).time()
                

                # Odczytaj parkingID na podstawie parkingName
                cursor = connection.cursor()
                sql_parking_id = "SELECT parkingID FROM Parking WHERE parkingName = %s"
                val_parking_id = (parking_name,)
                cursor.execute(sql_parking_id, val_parking_id)
                parking_id = cursor.fetchone()[0]  # Pobierz pierwszą kolumnę wyniku zapytania
                cursor.close()

                # Pobierz wartość availablePlaces dla wybranego parkingu i typu miejsca z tabeli spaceType
                cursor = connection.cursor()
                sql_space_type = "SELECT availablePlaces FROM SpaceType WHERE parkingID = %s AND spaceName = %s"
                val_space_type = (parking_id, space_type)
                cursor.execute(sql_space_type, val_space_type)
                available_places = cursor.fetchone()[0]  # Pobierz pierwszą kolumnę wyniku zapytania
                cursor.close()

                # Sprawdź, czy dostępne miejsca są większe niż 0
                if available_places > 0:
                    # Zapisz dane do tabeli Reservation
                    cursor = connection.cursor()
                    sql_reservation = "INSERT INTO Reservations (userID, parkingName, arrivalTime, departureTime, reservationDate) VALUES (%s, %s, %s, %s, %s)"
                    val_reservation = (userID, parking_name,  arrival_hour, departure_time, arrival_date)
                    cursor.execute(sql_reservation, val_reservation)
                    connection.commit()
                    
                    # Dodaj 10 punktów do kolumny score w tabeli Users
                    sql_update_score = "UPDATE Users SET score = score + 10 WHERE userID = %s"
                    val_update_score = (userID,)
                    cursor.execute(sql_update_score, val_update_score)
                    connection.commit()

                    cursor.close()

                    # Przekieruj użytkownika na stronę bookingDetalis po złożeniu rezerwacji
                    return render_template("bookingDetails.html", selected_vehicle=vehicle, 
                        selected_parking=parking_name, arrival_time=arrival_time, 
                        departure_time=departure_time, space_type=space_type)
                else:
                    # Przekaż komunikat o braku miejsc 
                    flash("Brak dostępnych miejsc tego typu. Proszę wybrać inne miejsce lub spróbować później.", 'warning')
                    # Przekieruj użytkownika z powrotem do strony rezerwacji
                    return redirect(url_for('booking'))

        return render_template("booking.html", vehicles=vehicles, parkings=parkings)

# rezerwacja 4.4
@app.route('/get_space_types', methods=['GET'])
def get_space_types():
    # Otrzymaj parkingName z parametrów zapytania
    parking_name = request.args.get('parkingName')
    print(parking_name)

    # Pobierz parkingID na podstawie parkingName z tabeli Parking
    cursor = connection.cursor()
    sql_parking_id = "SELECT parkingID FROM Parking WHERE parkingName = %s"
    val_parking_id = (parking_name,)
    cursor.execute(sql_parking_id, val_parking_id)
    result = cursor.fetchone()

    # Sprawdź, czy udało się pobrać parkingID
    if result:
        parking_id = result[0]

        # Pobierz dane o miejscach parkingowych na podstawie uzyskanego parkingID
        sql_space_types = "SELECT spaceID, spaceName FROM SpaceType WHERE parkingID = %s"
        val_space_types = (parking_id,)
        cursor.execute(sql_space_types, val_space_types)
        space_types = cursor.fetchall()

        return jsonify(space_types)

# aktualna rezerwacja 4.5
@app.route('/currentBooking')
def currentBooking():
    # Sprawdź, czy użytkownik jest zalogowany
    if 'logged_in' in session and session['logged_in']:
        email = session['email']

        # Pobierz dane użytkownika z bazy danych na podstawie emaila
        cursor = connection.cursor()
        sql_user = "SELECT userID, name FROM Users WHERE email = %s"
        val_user = (email,)
        cursor.execute(sql_user, val_user)
        user_data = cursor.fetchone()

        # Sprawdź, czy udało się pobrać dane użytkownika
        if user_data:
            # Pobierz userID z danych użytkownika
            user_id = user_data[0]

            # Pobierz obecny czas
            current_time_utc = datetime.now(timezone.utc)

            # Pobierz aktualne rezerwacje dla zalogowanego użytkownika z bazy danych
            cursor = connection.cursor()
            sql_current_bookings = "SELECT * FROM Reservations WHERE userID = %s AND reservationDate >= %s AND departureTime <=%s ORDER BY reservationDate, arrivalTime"
            val_current_bookings = (user_id, current_time_utc.date(), current_time_utc)
            cursor.execute(sql_current_bookings, val_current_bookings)
            current_bookings = cursor.fetchall()

            cursor.close()

            # Przygotuj listę rezerwacji z ich identyfikatorami
            reservations_with_ids = [{'reservationID': booking[0], 'userID': booking[1], 'parkingName': booking[2], 'arrivalTime': booking[3], 
                                      'departureTime': booking[4], 'reservationDate': booking[5]} for booking in current_bookings]

            return render_template("currentBooking.html", current_bookings=reservations_with_ids)

        else:
            flash('Nie można znaleźć użytkownika w bazie danych.', 'danger')
            return redirect(url_for('login'))
    else:
        # Obsłuż przypadek, gdy użytkownik nie jest zalogowany
        flash('Musisz być zalogowany, aby wyświetlić aktualne rezerwacje.', 'warning')
        return redirect(url_for('login'))


# szczegóły rezerwacji 5.2
@app.route('/bookingDetails')
def bookingDetails():
    selected_vehicle = request.args.get('vehicle')
    selected_parking = request.args.get('parking')
    arrival_time = request.args.get('arrival_time')
    departure_time = request.args.get('departure_time')
    space_type = request.args.get('space_type')

    return render_template("bookingDetails.html", selected_vehicle=selected_vehicle,
                           selected_parking=selected_parking,
                           arrival_time=arrival_time, departure_time=departure_time,
                           space_type=space_type)

# powiadomienie 5.3
@app.route('/setNotification', methods=['POST'])
def set_notification():
    if 'logged_in' in session and session['logged_in']:
        reservationId = request.form.get('reservationId')
        app.logger.info(f"Received reservation_id: {reservationId}")
        notification_time_str = request.form.get('notification_time')

        try:
            notification_time = datetime.strptime(notification_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Nieprawidłowy format czasu powiadomienia.', 'danger')
            return redirect(url_for('currentBooking'))

        # Zapisz czas powiadomienia w bazie danych
        cursor = connection.cursor()
        try:
            sql_update_notification = "UPDATE Reservations SET  notificationTime = %s WHERE reservationID = %s"
            val_update_notification = (notification_time, reservationId)
            cursor.execute(sql_update_notification, val_update_notification)
            connection.commit()
            flash('Czas powiadomienia został ustawiony.', 'success')
        except Exception as e:
            connection.rollback()
            flash(f'Błąd przy aktualizacji czasu powiadomienia: {str(e)}', 'danger')
        finally:
            cursor.close()

        return redirect(url_for('currentBooking'))
    else:
        flash('Musisz być zalogowany, aby ustawić powiadomienie.', 'warning')
        return redirect(url_for('login'))
    
# nawigacja 5.4
@app.route('/userRoad')
def userRoad():
    return render_template("userRoad.html")

# płatność 6
@app.route('/payments') 
def payments():
    return render_template("payments.html")

# potwierdzenie 7 
@app.route('/confirmation') 
def confirmation():
    return render_template("confirmation.html")

if __name__ == '__main__':
    app.run(debug=True)
