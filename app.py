import csv
import io
import json
import sqlite3

from flask import Flask, redirect, render_template, request, send_file, url_for

app = Flask(__name__)
DB_PATH = "scoring.db"


def load_scoring_criteria():
    with open("scoring_criteria.json", "r") as file:
        return json.load(file)


def init_db():
    with app.app_context():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Create scores table with dynamic columns based on scoring criteria
        criteria = load_scoring_criteria()

        # Start with base columns
        columns = [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "contestant TEXT NOT NULL",
            "rotation INTEGER NOT NULL",
        ]

        # Add a column for each scoring criterion
        for criterion in criteria["scoring_criteria"]:
            column_name = criterion["column_name"]
            columns.append(f"{column_name} INTEGER")

        # Add total score column
        columns.append("total_score INTEGER")

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
    station_num = -1
    criteria = load_scoring_criteria()

    if request.method == "POST":
        contestant = request.form.get("contestant")
        rotation = request.form.get("rotation")

        # Collect scores from form
        scores = {}
        total_score = 0

        for criterion in criteria["scoring_criteria"]:
            column_name = criterion["column_name"]
            if column_name in request.form:
                score = int(request.form[column_name])
                scores[column_name] = score
                total_score += score

        # Insert into database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Build the SQL query dynamically
        columns = ["contestant", "rotation"] + list(scores.keys()) + ["total_score"]
        placeholders = ["?"] * (len(columns))
        values = [contestant, rotation] + list(scores.values()) + [total_score]

        query = f"INSERT INTO scores ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        c.execute(query, values)

        conn.commit()
        conn.close()

        return redirect(url_for("index"))
    # For GET requests with query parameter
    elif request.method == "GET" and "station" in request.args:
        station_num = request.args.get("station", -1)

    print(f"Station Num: {station_num}")
    return render_template(
        "index.html", station_num=station_num, criteria=criteria["scoring_criteria"]
    )


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
        ORDER BY total_score DESC
    """)

    results = c.fetchall()
    criteria = load_scoring_criteria()

    return render_template(
        "results.html", results=results, criteria=criteria["scoring_criteria"]
    )


@app.route("/download-csv")
def download_csv():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM scores ORDER BY total_score DESC")
    results = c.fetchall()

    criteria = load_scoring_criteria()

    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    header = ["Contestant", "Rotation"]
    for criterion in criteria["scoring_criteria"]:
        header.append(criterion["name"])
    header.append("Total Score")
    writer.writerow(header)

    # Write data rows
    for result in results:
        row = [result["contestant"], result["rotation"]]
        for criterion in criteria["scoring_criteria"]:
            row.append(result[criterion["column_name"]])
        row.append(result["total_score"])
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
