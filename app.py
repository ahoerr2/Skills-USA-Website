import csv
import io
import sqlite3

from flask import Flask, redirect, render_template, request, send_file, url_for

app = Flask(__name__)
DB_PATH = "scoring.db"


def init_db():
    with app.app_context():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Start with base columns
        columns = [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "contestant TEXT NOT NULL",
            "rotation INTEGER NOT NULL",
            "station INTEGER NOT NULL",
            "score INTEGER NOT NULL",
        ]

        # Create the table
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS scores (
                {", ".join(columns)}
            )
        """)

        # Clear existing data (for testing)
        c.execute("DELETE FROM scores")
        c.execute("DELETE FROM sqlite_sequence WHERE name='scores'")

        conn.commit()
        conn.close()
        print("Database initialized successfully")


init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    station_num = "-1"

    if request.method == "POST":
        contestant = request.form.get("contestant")
        rotation = request.form.get("rotation")
        station = request.form.get("station_num")
        score = request.form.get("score")

        # Insert into database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Build the SQL query dynamically
        columns = ["contestant", "rotation", "station", "score"]
        placeholders = ["?"] * (len(columns))
        values = [contestant, rotation, station, score]

        query = f"INSERT INTO scores ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        c.execute(query, values)

        conn.commit()
        conn.close()

        return redirect(url_for("index", station=station))
    # For GET requests with query parameter
    elif request.method == "GET" and "station" in request.args:
        station_num = request.args.get("station", "-1")

    print(f"Station Num: {station_num}")
    return render_template("index.html", station_num=station_num)


@app.route("/stations")
def stations():
    # Renders the stations QR generator page
    return render_template("stations.html")


@app.route("/results")
def results():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT * FROM scores
        ORDER BY contestant DESC
    """)

    results = c.fetchall()

    return render_template("results.html", results=results)


@app.route("/download-csv")
def download_csv():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM scores ORDER BY contestant DESC")
    results = c.fetchall()

    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    header = ["Contestant", "Rotation", "Station", "Score"]
    writer.writerow(header)

    # Write data rows
    for result in results:
        row = [
            result["contestant"],
            result["rotation"],
            result["station"],
            result["score"],
        ]
        writer.writerow(row)

    # Prepare the output for download
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="scoring_results.csv",
    )


if __name__ == "__main__":
    app.run(debug=True)
