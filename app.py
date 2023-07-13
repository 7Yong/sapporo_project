from flask import Flask, render_template, request, jsonify
import random
import requests
import mysql.connector

app = Flask(__name__)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "satporo_annotation",
}

# 디비 커넥션 객체를 저장할 전역 변수
db = None

# 랜덤 값 범위
value_ranges = {
    "touchcare_place": ["방문", "냉장고", "화장실", "현관"],
    "weather": ["맑음", "흐림", "비", "눈"],
    "time": list(range(25)),
    "temperature": list(range(-12, 31)),
    "airpressure": list(range(2001)),
    "touchcare_many": list(range(101)),
}

# 기본 값
default_values = {
    "touchcare_place": random.choice(value_ranges["touchcare_place"]),
    "weather": random.choice(value_ranges["weather"]),
    "time": random.choice(value_ranges["time"]),
    "temperature": random.choice(value_ranges["temperature"]),
    "airpressure": random.choice(value_ranges["airpressure"]),
    "touchcare_many": random.choice(value_ranges["touchcare_many"]),
}


# 디비 커넥션 맺기
def connect_to_database():
    global db
    db = mysql.connector.connect(**db_config)
    print("디비에 연결되었습니다.")


# 디비 커넥션 닫기
def disconnect_from_database():
    global db
    if db:
        db.close()
        print("디비 연결이 종료되었습니다.")


# API 요청 시작 시 커넥션 맺기
@app.before_request
def before_request():
    connect_to_database()


# API 요청 종료 시 커넥션 닫기
@app.teardown_request
def teardown_request(exception=None):
    disconnect_from_database()


@app.route("/api/save_annotations", methods=["POST"])
def save_annotation():
    # POST 요청으로 전달된 데이터 가져오기
    data = request.form.to_dict()

    # 데이터베이스에 저장할 값 추출
    touchcare_place = data.get("touchcare_place")
    weather = data.get("weather")
    time = data.get("time")
    temperature = data.get("temperature")
    airpressure = data.get("airpressure")
    touchcare_many = data.get("touchcare_many")
    message = data.get("message")

    # annotations 테이블에 데이터 삽입
    cursor = db.cursor()
    query = "INSERT INTO annotations (touchcare_place, weather, time, temperature, airpressure, touchcare_many, message) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    values = (
        touchcare_place,
        weather,
        time,
        temperature,
        airpressure,
        touchcare_many,
        message,
    )

    try:
        cursor.execute(query, values)
        db.commit()
        cursor.close()
        return jsonify(data)
    except mysql.connector.Error as error:
        return f"An error occurred while saving the data: {str(error)}"


@app.route("/api/refresh_values", methods=["GET"])
def refresh_values():
    # 랜덤 값을 업데이트하고 새로운 값을 응답으로 전달
    default_values = {
        field: random.choice(value_ranges[field]) for field in value_ranges
    }
    return jsonify(default_values)


@app.route("/api/current_weather", methods=["GET"])
def current_weather():
    try:
        # OpenWeather API 호출
        response = requests.get(
            "https://api.openweathermap.org/data/3.0/onecall?lat=43&lon=141&units=metric&lang=kr&exclude=minutely,hourly,daily&appid=c8c4a39fee42522c6f3169616867d38b"
        )
        data = response.json()

        # 필요한 데이터 추출
        current = data.get("current", {})
        weather = current.get("weather", [])
        temperature = current.get("temp")
        airpressure = current.get("pressure")

        return jsonify(
            {
                "weather": weather[0]["description"] if weather else "",
                "temperature": temperature if temperature else "",
                "airpressure": airpressure if airpressure else "",
            }
        )
    except requests.RequestException as error:
        return f"An error occurred while retrieving the current weather: {str(error)}"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # 폼으로부터 전달된 데이터 받기
        message = request.form.get("message")
        checkbox_table = request.form.get("checkbox_table")

        if checkbox_table == "above":
            touchcare_place = request.form.get("touchcare_place")
            weather = request.form.get("weather")
            time = request.form.get("time")
            temperature = request.form.get("temperature")
            airpressure = request.form.get("airpressure")
            touchcare_many = request.form.get("touchcare_many")
        elif checkbox_table == "below":
            touchcare_place = request.form.get("current-touchcare_place")
            weather = request.form.get("current-weather")
            time = request.form.get("current-time")
            temperature = request.form.get("current-temperature")
            airpressure = request.form.get("current-airpressure")
            touchcare_many = request.form.get("current-touchcare_many")
        else:
            return "Invalid checkbox_table value"

        # API 호출하여 데이터 전송
        response = requests.post(
            "http://localhost:5000/api/save_annotations",
            data={
                "touchcare_place": touchcare_place,
                "weather": weather,
                "time": time,
                "temperature": temperature,
                "airpressure": airpressure,
                "touchcare_many": touchcare_many,
                "message": message,
            },
        )

        if response.status_code == 200:
            # 서버로부터 받은 데이터를 JSON으로 변환
            saved_data = response.json()

            # HTML에 저장된 데이터 출력
            return render_template("index.html", values=saved_data)
        else:
            return f"An error occurred while saving the data: {response.text}"

    # 기본 값 전달
    return render_template("index.html", values=default_values)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
