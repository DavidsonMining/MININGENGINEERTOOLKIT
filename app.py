from flask import Flask, render_template, request
app = Flask(__name__)
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/stripping-ratio", methods=["GET", "POST"])
def stripping_ratio():
    result = None
    if request.method == "POST":
        overburden = float(request.form["overburden"])
        ore = float(request.form["ore"])
        if ore == 0:
            result = "Error: Ore volume cannot be zero."
        else:
            result = overburden / ore
    return render_template("stripping_ratio.html", result=result)
@app.route("/porosity", methods=["GET", "POST"])
def porosity():
    result = None
    if request.method == "POST":
        pore_volume = float(request.form["pore_volume"])
        total_volume = float(request.form["total_volume"])
        if total_volume == 0:
            result = "Error: Total volume cannot be zero."
        else:
            result = (pore_volume / total_volume) * 100
    return render_template("porosity.html", result=result)
@app.route("/density", methods=["GET", "POST"])
def density():
    result = None
    if request.method == "POST":
        mass = float(request.form["mass"])
        volume = float(request.form["volume"])
        mass_unit = request.form["mass_unit"]
        volume_unit = request.form["volume_unit"]
        if mass_unit == "g":
            mass = mass / 1000
        if volume_unit == "cm3":
            volume = volume / 1000000
        if volume == 0:
            result = "Error: Volume cannot be zero."
        else:
            result = mass / volume
    return render_template("density.html", result=result)
@app.route("/grade-recovery", methods=["GET", "POST"])
def grade_recovery():
    result = None
    if request.method == "POST":
        ore_feed = float(request.form["ore_feed"])
        ore_grade = float(request.form["ore_grade"])
        concentrate = float(request.form["concentrate"])
        concentrate_grade = float(request.form["concentrate_grade"])
        denominator = ore_feed * ore_grade
        if denominator == 0:
            result = "Error: Ore feed and ore grade cannot produce zero metal content."
        else:
            result = (concentrate * concentrate_grade) / denominator * 100
    return render_template("grade_recovery.html", result=result)
@app.route("/bulk-density", methods=["GET", "POST"])
def bulk_density():
    result = None
    result_unit = None
    if request.method == "POST":
        mass = float(request.form["mass"])
        volume = float(request.form["volume"])
        mass_unit = request.form["mass_unit"]
        volume_unit = request.form["volume_unit"]
        # Convert mass to kilograms
        if mass_unit == "g":
            mass = mass / 1000
        # Convert volume to cubic metres
        if volume_unit == "cm3":
            volume = volume / 1000000
        if volume == 0:
            result = "Error: Volume cannot be zero."
        else:
            result = mass / volume
            result_unit = "kg/m³"
    return render_template(
        "bulk_density.html",
        result=result,
        result_unit=result_unit
    )
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5001)