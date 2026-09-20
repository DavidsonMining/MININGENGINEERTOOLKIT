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


@app.route("/tonnage", methods=["GET", "POST"])
def tonnage():
    result = None

    if request.method == "POST":
        volume = float(request.form["volume"])
        density = float(request.form["density"])

        result = volume * density

    return render_template("tonnage.html", result=result)
@app.route("/haulage", methods=["GET", "POST"])
def haulage():
    result = None

    if request.method == "POST":
        payload = float(request.form["payload"])
        cycle_time = float(request.form["cycle_time"])
        operating_hours = float(request.form["operating_hours"])

        if cycle_time == 0:
            result = "Error: Cycle time cannot be zero."
        else:
            result = payload * ((operating_hours * 60) / cycle_time)

    return render_template("haulage.html", result=result)
@app.route("/blasting", methods=["GET", "POST"])
def blasting():
    result = None
    volume = None

    if request.method == "POST":
        burden = float(request.form["burden"])
        spacing = float(request.form["spacing"])
        bench_height = float(request.form["bench_height"])
        number_of_holes = int(request.form["number_of_holes"])
        explosive_mass = float(request.form["explosive_mass"])

        volume = burden * spacing * bench_height * number_of_holes

        if volume == 0:
            result = "Error: Blast volume cannot be zero."
        else:
            result = explosive_mass / volume

    return render_template(
        "blasting.html",
        result=result,
        volume=volume
    )
@app.route("/pit-volume", methods=["GET", "POST"])
def pit_volume():
    result = None

    if request.method == "POST":
        length = float(request.form["length"])
        width = float(request.form["width"])
        height = float(request.form["height"])

        result = length * width * height

    return render_template("pit_volume.html", result=result)
@app.route("/ore-grade", methods=["GET", "POST"])
def ore_grade():
    result = None

    if request.method == "POST":
        metal_content = float(request.form["metal_content"])
        ore_mass = float(request.form["ore_mass"])

        if ore_mass == 0:
            result = "Error: Ore mass cannot be zero."
        else:
            # Convert tonnes of ore to kilograms
            ore_mass_kg = ore_mass * 1000

            result = (metal_content / ore_mass_kg) * 100

    return render_template("ore_grade.html", result=result)
@app.route("/recovery", methods=["GET", "POST"])
def recovery():
    result = None

    if request.method == "POST":
        recovered_metal = float(request.form["recovered_metal"])
        available_metal = float(request.form["available_metal"])

        if available_metal == 0:
            result = "Error: Available metal cannot be zero."
        else:
            result = (recovered_metal / available_metal) * 100

    return render_template("recovery.html", result=result)
@app.route("/moisture", methods=["GET", "POST"])
def moisture():
    result = None

    if request.method == "POST":
        wet_mass = float(request.form["wet_mass"])
        dry_mass = float(request.form["dry_mass"])

        if dry_mass == 0:
            result = "Error: Dry mass cannot be zero."
        else:
            result = ((wet_mass - dry_mass) / dry_mass) * 100

    return render_template("moisture.html", result=result)
@app.route("/specific-gravity", methods=["GET", "POST"])
def specific_gravity():
    result = None

    if request.method == "POST":
        material_density = float(request.form["material_density"])
        water_density = float(request.form["water_density"])

        if water_density == 0:
            result = "Error: Water density cannot be zero."
        else:
            result = material_density / water_density

    return render_template(
        "specific_gravity.html",
        result=result
    )
@app.route("/mine-life", methods=["GET", "POST"])
def mine_life():
    result = None

    if request.method == "POST":
        reserves = float(request.form["reserves"])
        production = float(request.form["production"])

        if production == 0:
            result = "Error: Annual production cannot be zero."
        else:
            result = reserves / production

    return render_template("mine_life.html", result=result)
@app.route("/equipment-productivity", methods=["GET", "POST"])
def equipment_productivity():
    result = None

    if request.method == "POST":
        bucket_capacity = float(request.form["bucket_capacity"])
        cycles_per_hour = float(request.form["cycles_per_hour"])
        operating_hours = float(request.form["operating_hours"])

        result = bucket_capacity * cycles_per_hour * operating_hours

    return render_template(
        "equipment_productivity.html",
        result=result
    )
@app.route("/truck-payload", methods=["GET", "POST"])
def truck_payload():
    payload = None
    total_hauled = None

    if request.method == "POST":
        truck_capacity = float(request.form["truck_capacity"])
        density = float(request.form["density"])
        load_factor = float(request.form["load_factor"])
        trips = int(request.form["trips"])

        payload = truck_capacity * density * (load_factor / 100)
        total_hauled = payload * trips

    return render_template(
        "truck_payload.html",
        payload=payload,
        total_hauled=total_hauled
    )
@app.route("/cut-fill", methods=["GET", "POST"])
def cut_fill():
    cut_volume = None
    fill_volume = None
    net_balance = None

    if request.method == "POST":
        cut_area = float(request.form["cut_area"])
        cut_depth = float(request.form["cut_depth"])

        fill_area = float(request.form["fill_area"])
        fill_depth = float(request.form["fill_depth"])

        cut_volume = cut_area * cut_depth
        fill_volume = fill_area * fill_depth
        net_balance = cut_volume - fill_volume

    return render_template(
        "cut_fill.html",
        cut_volume=cut_volume,
        fill_volume=fill_volume,
        net_balance=net_balance
    )
@app.route("/explosive-charge", methods=["GET", "POST"])
def explosive_charge():
    result = None

    if request.method == "POST":
        number_of_holes = int(request.form["number_of_holes"])
        charge_per_hole = float(request.form["charge_per_hole"])

        result = number_of_holes * charge_per_hole

    return render_template(
        "explosive_charge.html",
        result=result
    )
@app.route("/fuel-consumption", methods=["GET", "POST"])
def fuel_consumption():
    total_fuel = None
    total_cost = None

    if request.method == "POST":
        fuel_rate = float(request.form["fuel_rate"])
        operating_hours = float(request.form["operating_hours"])
        fuel_price = float(request.form["fuel_price"])

        total_fuel = fuel_rate * operating_hours
        total_cost = total_fuel * fuel_price

    return render_template(
        "fuel_consumption.html",
        total_fuel=total_fuel,
        total_cost=total_cost
    )
@app.route("/equipment-operating-cost", methods=["GET", "POST"])
def equipment_operating_cost():
    total_cost = None

    if request.method == "POST":
        fuel_cost_per_hour = float(request.form["fuel_cost_per_hour"])
        operating_hours = float(request.form["operating_hours"])
        maintenance_cost_per_hour = float(request.form["maintenance_cost_per_hour"])
        other_cost_per_hour = float(request.form["other_cost_per_hour"])

        total_cost_per_hour = (
            fuel_cost_per_hour
            + maintenance_cost_per_hour
            + other_cost_per_hour
        )

        total_cost = total_cost_per_hour * operating_hours

    return render_template(
        "equipment_operating_cost.html",
        total_cost=total_cost
    )
@app.route("/mining-formulas")
def mining_formulas():
    return render_template("mining_formulas.html")
@app.route("/mining-terms")
def mining_terms():
    return render_template("mining_terms.html")
@app.route("/study-reference")
def study_reference():
    return render_template("study_reference.html")
@app.route("/mining-methods")
def mining_methods():
    return render_template("mining_methods.html")
@app.route("/geology")
def geology():
    return render_template("geology.html")
@app.route("/mining-equipment")
def mining_equipment():
    return render_template("mining_equipment.html")
@app.route("/mine-planning")
def mine_planning():
    return render_template("mine_planning.html")
@app.route("/rock-blasting")
def rock_blasting():
    return render_template("rock_blasting.html")
@app.route("/mineral-processing")
def mineral_processing():
    return render_template("mineral_processing.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5001)
