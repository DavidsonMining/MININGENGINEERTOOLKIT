import os
import re

from flask import Flask, render_template, request, redirect, url_for
import requests
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError, ClientError

from chat_memory import (
    create_chat,
    add_message,
    get_chats,
    get_messages,
    get_chat,
    delete_chat
)

from topic_knowledge import find_topic_answer


# ============================================================
# SETUP
# ============================================================

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None


def clean_ai_response(text):
    """Clean common markdown formatting."""
    if not text:
        return ""

    text = text.replace("**", "")
    text = text.replace("__", "")
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    return text.strip()


# ============================================================
# CHAT MEMORY HELPERS
# ============================================================

def make_chat_title(question):
    """
    Create a simple professional title from the first
    question in a conversation.
    """

    title = question.strip()

    title = re.sub(r"\s+", " ", title)

    title = title.strip(" .?!")

    if not title:
        return "New Chat"

    if len(title) > 45:
        title = title[:45].rsplit(" ", 1)[0] + "..."

    return title


def valid_chat_id(value):
    """
    Convert a chat ID to an integer safely.
    Returns None if the value is invalid.
    """

    try:
        chat_id = int(value)

        if chat_id <= 0:
            return None

        return chat_id

    except (TypeError, ValueError):
        return None


def conversation_context(chat_id, limit=12):
    """
    Build recent conversation history for Gemini.
    This allows Gemini to understand previous messages
    from the same conversation.
    """

    messages = get_messages(chat_id)

    if not messages:
        return ""

    recent_messages = messages[-limit:]

    context_lines = []

    for message in recent_messages:

        role = message["role"]

        if role == "user":
            label = "Student"
        else:
            label = "Mining Engineer Toolkit AI"

        context_lines.append(
            f"{label}: {message['content']}"
        )

    return "\n".join(context_lines)


def contextual_question(chat_id, question):
    """
    Add the previous student question when the new question
    looks like a follow-up.

    Example:

        Student: What is open-pit mining?
        Student: Give me an example.

    The second question becomes:

        Previous student question: What is open-pit mining?

        Follow-up question: Give me an example.
    """

    messages = get_messages(chat_id)

    if not messages:
        return question

    previous_user_question = None

    # The current user message has already been saved before
    # this function is called, so skip the latest message.
    for message in reversed(messages[:-1]):

        if message["role"] == "user":

            previous_user_question = message["content"]

            break

    if not previous_user_question:
        return question

    follow_up_phrases = [
        "give me an example",
        "give me an example of it",
        "give an example",
        "another example",
        "explain that",
        "explain it",
        "explain again",
        "simplify that",
        "make it simple",
        "what do you mean",
        "how does it work",
        "how is it used",
        "why is it important",
        "what are the advantages",
        "what are the disadvantages",
        "what is the formula",
        "what formula do i use",
        "show me how",
        "show me an example"
    ]

    question_lower = question.lower().strip()

    is_follow_up = any(
        phrase in question_lower
        for phrase in follow_up_phrases
    )

    if is_follow_up:

        return (
            f"Previous student question: "
            f"{previous_user_question}\n\n"
            f"Follow-up question: {question}"
        )

    return question


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# CALCULATORS
# ============================================================

@app.route("/stripping-ratio", methods=["GET", "POST"])
def stripping_ratio():
    result = None
    error = None

    if request.method == "POST":
        try:
            overburden = float(request.form["overburden"])
            ore = float(request.form["ore"])

            if ore == 0:
                error = "Ore cannot be zero."
            else:
                result = overburden / ore

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "stripping_ratio.html",
        result=result,
        error=error
    )


@app.route("/porosity", methods=["GET", "POST"])
def porosity():
    result = None
    error = None

    if request.method == "POST":
        try:
            pore_volume = float(request.form["pore_volume"])
            total_volume = float(request.form["total_volume"])

            if total_volume == 0:
                error = "Total volume cannot be zero."
            else:
                result = (pore_volume / total_volume) * 100

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "porosity.html",
        result=result,
        error=error
    )


@app.route("/density", methods=["GET", "POST"])
def density():
    result = None
    error = None

    if request.method == "POST":
        try:
            mass = float(request.form["mass"])
            mass_unit = request.form["mass_unit"]

            volume = float(request.form["volume"])
            volume_unit = request.form["volume_unit"]

            if mass_unit == "g":
                mass = mass / 1000

            if volume_unit == "cm3":
                volume = volume / 1_000_000

            if volume == 0:
                error = "Volume cannot be zero."
            else:
                result = mass / volume

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "density.html",
        result=result,
        error=error
    )


@app.route("/grade-recovery", methods=["GET", "POST"])
def grade_recovery():
    result = None
    error = None

    if request.method == "POST":
        try:
            concentrate = float(request.form["concentrate"])
            concentrate_grade = float(request.form["concentrate_grade"])
            ore_feed = float(request.form["ore_feed"])
            ore_grade = float(request.form["ore_grade"])

            if ore_feed == 0 or ore_grade == 0:
                error = "Ore feed and ore grade cannot be zero."
            else:
                result = (
                    (concentrate * concentrate_grade)
                    / (ore_feed * ore_grade)
                ) * 100

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "grade_recovery.html",
        result=result,
        error=error
    )


@app.route("/bulk-density", methods=["GET", "POST"])
def bulk_density():
    result = None
    error = None

    if request.method == "POST":
        try:
            mass = float(request.form["mass"])
            volume = float(request.form["volume"])

            if volume == 0:
                error = "Volume cannot be zero."
            else:
                result = mass / volume

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "bulk_density.html",
        result=result,
        error=error
    )


@app.route("/tonnage", methods=["GET", "POST"])
def tonnage():
    result = None
    error = None

    if request.method == "POST":
        try:
            volume = float(request.form["volume"])
            density = float(request.form["density"])

            result = volume * density

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "tonnage.html",
        result=result,
        error=error
    )


@app.route("/haulage", methods=["GET", "POST"])
def haulage():
    result = None
    error = None

    if request.method == "POST":
        try:
            payload = float(request.form["payload"])
            operating_hours = float(request.form["operating_hours"])
            cycle_time = float(request.form["cycle_time"])

            if cycle_time == 0:
                error = "Cycle time cannot be zero."
            else:
                result = payload * (
                    (operating_hours * 60) / cycle_time
                )

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "haulage.html",
        result=result,
        error=error
    )


@app.route("/blasting", methods=["GET", "POST"])
def blasting():
    result = None
    error = None

    if request.method == "POST":
        try:
            burden = float(request.form["burden"])
            spacing = float(request.form["spacing"])
            bench_height = float(request.form["bench_height"])
            number_of_holes = float(request.form["number_of_holes"])
            explosive_mass = float(request.form["explosive_mass"])

            blast_volume = (
                burden
                * spacing
                * bench_height
                * number_of_holes
            )

            if blast_volume == 0:
                error = "Blast volume cannot be zero."
            else:
                powder_factor = explosive_mass / blast_volume

                result = {
                    "blast_volume": blast_volume,
                    "powder_factor": powder_factor
                }

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "blasting.html",
        result=result,
        error=error
    )


@app.route("/pit-volume", methods=["GET", "POST"])
def pit_volume():
    result = None
    error = None

    if request.method == "POST":
        try:
            length = float(request.form["length"])
            width = float(request.form["width"])
            height = float(request.form["height"])

            result = length * width * height

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "pit_volume.html",
        result=result,
        error=error
    )


@app.route("/ore-grade", methods=["GET", "POST"])
def ore_grade():
    result = None
    error = None

    if request.method == "POST":
        try:
            metal_content = float(request.form["metal_content"])
            ore_mass = float(request.form["ore_mass"])

            if ore_mass == 0:
                error = "Ore mass cannot be zero."
            else:
                ore_mass_kg = ore_mass * 1000
                result = (metal_content / ore_mass_kg) * 100

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "ore_grade.html",
        result=result,
        error=error
    )


@app.route("/recovery", methods=["GET", "POST"])
def recovery():
    result = None
    error = None

    if request.method == "POST":
        try:
            recovered_metal = float(request.form["recovered_metal"])
            available_metal = float(request.form["available_metal"])

            if available_metal == 0:
                error = "Available metal cannot be zero."
            else:
                result = (
                    recovered_metal / available_metal
                ) * 100

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "recovery.html",
        result=result,
        error=error
    )


@app.route("/moisture", methods=["GET", "POST"])
def moisture():
    result = None
    error = None

    if request.method == "POST":
        try:
            wet_mass = float(request.form["wet_mass"])
            dry_mass = float(request.form["dry_mass"])

            if dry_mass == 0:
                error = "Dry mass cannot be zero."
            else:
                result = (
                    (wet_mass - dry_mass)
                    / dry_mass
                ) * 100

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "moisture.html",
        result=result,
        error=error
    )


@app.route("/specific-gravity", methods=["GET", "POST"])
def specific_gravity():
    result = None
    error = None

    if request.method == "POST":
        try:
            material_density = float(
                request.form["material_density"]
            )

            water_density = float(
                request.form["water_density"]
            )

            if water_density == 0:
                error = "Water density cannot be zero."
            else:
                result = material_density / water_density

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "specific_gravity.html",
        result=result,
        error=error
    )


@app.route("/mine-life", methods=["GET", "POST"])
def mine_life():
    result = None
    error = None

    if request.method == "POST":
        try:
            reserves = float(request.form["reserves"])
            annual_production = float(
                request.form["annual_production"]
            )

            if annual_production == 0:
                error = "Annual production cannot be zero."
            else:
                result = reserves / annual_production

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "mine_life.html",
        result=result,
        error=error
    )


@app.route("/equipment-productivity", methods=["GET", "POST"])
def equipment_productivity():
    result = None
    error = None

    if request.method == "POST":
        try:
            bucket_capacity = float(
                request.form["bucket_capacity"]
            )

            cycles_per_hour = float(
                request.form["cycles_per_hour"]
            )

            operating_hours = float(
                request.form["operating_hours"]
            )

            result = (
                bucket_capacity
                * cycles_per_hour
                * operating_hours
            )

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "equipment_productivity.html",
        result=result,
        error=error
    )


@app.route("/truck-payload", methods=["GET", "POST"])
def truck_payload():
    result = None
    error = None

    if request.method == "POST":
        try:
            truck_capacity = float(
                request.form["truck_capacity"]
            )

            density = float(
                request.form["density"]
            )

            load_factor = float(
                request.form["load_factor"]
            )

            trips = float(
                request.form["trips"]
            )

            payload_per_trip = (
                truck_capacity
                * density
                * (load_factor / 100)
            )

            total_hauled = payload_per_trip * trips

            result = {
                "payload_per_trip": payload_per_trip,
                "total_hauled": total_hauled
            }

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "truck_payload.html",
        result=result,
        error=error
    )


@app.route("/cut-fill", methods=["GET", "POST"])
def cut_fill():
    result = None
    error = None

    if request.method == "POST":
        try:
            cut_area = float(request.form["cut_area"])
            cut_depth = float(request.form["cut_depth"])

            fill_area = float(request.form["fill_area"])
            fill_depth = float(request.form["fill_depth"])

            cut_volume = cut_area * cut_depth
            fill_volume = fill_area * fill_depth
            net_volume = cut_volume - fill_volume

            result = {
                "cut_volume": cut_volume,
                "fill_volume": fill_volume,
                "net_volume": net_volume
            }

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "cut_fill.html",
        result=result,
        error=error
    )


@app.route("/explosive-charge", methods=["GET", "POST"])
def explosive_charge():
    result = None
    error = None

    if request.method == "POST":
        try:
            number_of_charges = float(
                request.form["number_of_charges"]
            )

            charge_per_unit = float(
                request.form["charge_per_unit"]
            )

            result = number_of_charges * charge_per_unit

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "explosive_charge.html",
        result=result,
        error=error
    )


@app.route("/fuel-consumption", methods=["GET", "POST"])
def fuel_consumption():
    result = None
    error = None

    if request.method == "POST":
        try:
            fuel_rate = float(
                request.form["fuel_rate"]
            )

            operating_hours = float(
                request.form["operating_hours"]
            )

            fuel_price = float(
                request.form["fuel_price"]
            )

            total_fuel = (
                fuel_rate * operating_hours
            )

            total_cost = (
                total_fuel * fuel_price
            )

            result = {
                "total_fuel": total_fuel,
                "total_cost": total_cost
            }

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "fuel_consumption.html",
        result=result,
        error=error
    )


@app.route("/equipment-operating-cost", methods=["GET", "POST"])
def equipment_operating_cost():
    result = None
    error = None

    if request.method == "POST":
        try:
            fuel_cost_per_hour = float(
                request.form["fuel_cost_per_hour"]
            )

            maintenance_cost_per_hour = float(
                request.form["maintenance_cost_per_hour"]
            )

            other_cost_per_hour = float(
                request.form["other_cost_per_hour"]
            )

            operating_hours = float(
                request.form["operating_hours"]
            )

            hourly_cost = (
                fuel_cost_per_hour
                + maintenance_cost_per_hour
                + other_cost_per_hour
            )

            result = hourly_cost * operating_hours

        except (ValueError, KeyError):
            error = "Please enter valid numbers."

    return render_template(
        "equipment_operating_cost.html",
        result=result,
        error=error
    )


# ============================================================
# STUDY RESOURCES
# ============================================================

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


# ============================================================
# LOCAL TOOLKIT KNOWLEDGE
# ============================================================

LOCAL_KNOWLEDGE = {

    # ========================================================
    # MINING FUNDAMENTALS
    # ========================================================

    "what is mining":
        "Mining is the extraction of valuable minerals or other "
        "geological materials from the Earth for use by people "
        "and industry.",

    "mining":
        "Mining is the extraction of valuable minerals or other "
        "geological materials from the Earth. Mining may involve "
        "surface or underground methods depending on the location, "
        "geometry and characteristics of the deposit.",

    "ore":
        "Ore is naturally occurring material containing valuable "
        "minerals in a concentration that may allow economic "
        "extraction under suitable conditions.",

    "ore body":
        "An ore body is a naturally occurring concentration of "
        "valuable minerals that may be economically extractable "
        "under suitable conditions.",

    "ore deposit":
        "An ore deposit is a natural concentration of minerals "
        "that contains potentially valuable material. Its economic "
        "value depends on factors such as grade, tonnage, recovery, "
        "costs and prevailing economic conditions.",

    "mineral":
        "A mineral is a naturally occurring inorganic solid with "
        "an ordered atomic structure and a characteristic chemical "
        "composition or compositional range.",

    "gangue":
        "Gangue refers to unwanted or non-economic minerals "
        "associated with valuable minerals in an ore deposit.",

    "overburden":
        "Overburden is the soil, weathered material, rock or other "
        "material overlying a mineral deposit that must be removed "
        "to access the deposit.",

    "stripping":
        "Stripping is the removal of overburden or other waste "
        "material to expose and access an ore body.",

    "stripping ratio":
        "Stripping ratio is the amount of waste material that must "
        "be removed to obtain a unit amount of ore. "
        "Stripping Ratio = Overburden / Ore.",

    "bench":
        "A bench is a horizontal or near-horizontal working level "
        "or step formed during mining, particularly in open-pit "
        "operations.",

    "grade":
        "Grade is the concentration of a valuable mineral or metal "
        "in ore. It may be expressed in units such as percent, "
        "grams per tonne or parts per million depending on the "
        "commodity.",

    "ore grade":
        "Ore grade describes the concentration of a valuable mineral "
        "or metal in ore. The exact expression depends on the "
        "commodity and units being used.",

    "tonnage":
        "Tonnage is the mass of material, commonly expressed in "
        "tonnes. A simple estimate can be obtained from Volume × "
        "Density when the units are compatible.",

    "dilution":
        "Dilution is the inclusion of unwanted or low-grade material "
        "with the ore during mining. It can reduce the grade of "
        "material sent for processing.",

    "mining loss":
        "Mining loss refers to valuable material that is not recovered "
        "during the mining process. Losses can occur because of "
        "geological conditions, mining constraints, or operational "
        "limitations.",

    "recovery":
        "Recovery is the percentage of valuable metal successfully "
        "recovered from the material processed. "
        "Recovery = Recovered Metal / Available Metal × 100.",

    # ========================================================
    # MINING METHODS
    # ========================================================

    "open pit mining":
        "Open-pit mining is a surface mining method used to extract "
        "ore from a deposit near the surface. Waste and overburden "
        "are removed and the deposit is mined in benches. The method "
        "commonly uses equipment such as drills, excavators, loaders "
        "and haul trucks.",

    "open pit":
        "An open pit is a large surface excavation developed to "
        "extract a mineral deposit. Mining commonly proceeds through "
        "a series of benches while waste is removed to expose ore.",

    "underground mining":
        "Underground mining extracts mineral deposits below the "
        "surface using access and excavation workings such as shafts, "
        "declines, ramps, drifts, crosscuts and raises.",

    "room and pillar":
        "Room-and-pillar mining is an underground mining method in "
        "which material is extracted from rooms while pillars of "
        "material are left in place to support the roof. The layout "
        "and pillar dimensions depend on geological and geotechnical "
        "conditions.",

    "cut and fill":
        "Cut-and-fill mining is an underground method in which ore "
        "is extracted in successive slices and the mined-out space "
        "is filled before or during subsequent mining. It can be "
        "useful where ground control and selective extraction are "
        "important.",

    "cut and fill mining":
        "Cut-and-fill mining involves extracting ore in slices and "
        "filling the excavated area with suitable fill material. "
        "The filled area can provide a working platform and help "
        "support the surrounding ground.",

    "sublevel stoping":
        "Sublevel stoping is an underground mining method in which "
        "ore is extracted from a stope accessed from sublevels. "
        "It is generally associated with deposits that have suitable "
        "geometry and competent ground conditions.",

    "longwall mining":
        "Longwall mining is a high-production underground method "
        "commonly associated with tabular deposits such as coal. "
        "A longwall face is advanced while the roof behind the "
        "face is allowed to cave or is otherwise controlled.",

    "block caving":
        "Block caving is a large-scale underground mining method in "
        "which a large block of ore is undercut so that the rock "
        "mass fractures and caves under gravity. Broken ore is "
        "collected through drawpoints.",

    "shrinkage stoping":
        "Shrinkage stoping is an underground method where broken "
        "ore is temporarily left in the stope to provide a working "
        "platform and support, with ore removed progressively.",

    "cut and fill method":
        "In the cut-and-fill method, ore is mined in horizontal or "
        "inclined slices and the excavated space is subsequently "
        "filled. This method can provide good ground control and "
        "selectivity.",

    # ========================================================
    # GEOLOGY
    # ========================================================

    "geology":
        "Geology is the study of Earth's materials, structures, "
        "processes and history. In mining, geology helps identify "
        "and characterize mineral deposits and understand their "
        "distribution.",

    "rock":
        "A rock is a naturally occurring aggregate of one or more "
        "minerals or mineraloid materials. Rocks are commonly "
        "classified as igneous, sedimentary or metamorphic.",

    "igneous rock":
        "Igneous rocks form when molten rock material cools and "
        "solidifies. They may form below the Earth's surface as "
        "intrusive rocks or at the surface as extrusive rocks.",

    "sedimentary rock":
        "Sedimentary rocks form from the accumulation, compaction "
        "and cementation of sediments, or from chemical and biological "
        "processes at or near Earth's surface.",

    "metamorphic rock":
        "Metamorphic rocks form when existing rocks are altered by "
        "heat, pressure and chemically active fluids without completely "
        "melting.",

    "ore mineral":
        "An ore mineral is a mineral containing a valuable element "
        "or commodity that can potentially be recovered economically "
        "under suitable conditions.",

    "host rock":
        "Host rock is the rock surrounding or containing a mineral "
        "deposit. Its physical and geological properties can affect "
        "exploration, mining and ground stability.",

    "country rock":
        "Country rock refers to the surrounding rock into which a "
        "mineral deposit, vein or intrusion occurs.",

    "vein":
        "A vein is a mineral-filled fracture or zone in rock. Veins "
        "can contain economically valuable minerals and are important "
        "features in some mineral deposits.",

    "fault":
        "A fault is a fracture or zone of fractures in Earth's crust "
        "along which displacement has occurred. Faults can influence "
        "ore deposition, groundwater movement and rock stability.",

    "fold":
        "A fold is a bend or curvature in geological layers or rock "
        "strata produced by deformation.",

    "porosity":
        "Porosity is the percentage of void space in a rock or soil. "
        "Porosity = (Pore Volume / Total Volume) × 100.",

    "permeability":
        "Permeability describes the ability of a material to allow "
        "fluids to flow through connected pore spaces or fractures. "
        "It is different from porosity, which measures the amount "
        "of void space.",

    "grain density":
        "Grain density is the mass of the solid mineral grains divided "
        "by the volume occupied only by those grains, excluding pore "
        "spaces.",

    "specific gravity":
        "Specific gravity is the ratio of a material's density to "
        "the density of water under a specified reference condition. "
        "It has no units.",

    # ========================================================
    # MINERALOGY
    # ========================================================

    "mineralogy":
        "Mineralogy is the study of minerals, including their "
        "chemical composition, crystal structure, physical properties, "
        "formation and occurrence.",

    "crystal":
        "A crystal is a solid material whose atoms, ions or molecules "
        "are arranged in an ordered repeating structure.",

    "crystal structure":
        "Crystal structure describes the orderly arrangement of atoms, "
        "ions or molecules within a crystalline material.",

    "unit cell":
        "A unit cell is the smallest repeating structural unit that "
        "can be used to describe the three-dimensional crystal lattice "
        "of a crystalline material.",

    "mineral hardness":
        "Mineral hardness is the resistance of a mineral to scratching. "
        "It is commonly compared using the Mohs hardness scale.",

    "mohs scale":
        "The Mohs scale is a relative scale used to compare mineral "
        "hardness from talc at 1 to diamond at 10.",

    # ========================================================
    # MINERAL PROCESSING
    # ========================================================

    "mineral processing":
        "Mineral processing involves separating valuable minerals "
        "from unwanted gangue. Common stages include crushing, "
        "grinding, classification, concentration and dewatering.",

    "crushing":
        "Crushing is a size-reduction stage in mineral processing "
        "where large pieces of ore or rock are reduced to smaller "
        "particles.",

    "grinding":
        "Grinding is a further size-reduction stage in mineral "
        "processing. Mills are commonly used to produce finer "
        "particles for subsequent separation or concentration.",

    "classification":
        "Classification separates particles according to characteristics "
        "such as size or settling behavior. Hydrocyclones and screens "
        "are examples of equipment used in classification and sizing.",

    "flotation":
        "Froth flotation is a mineral-processing method that separates "
        "minerals based on differences in their surface properties. "
        "Selected particles can attach to air bubbles and be carried "
        "into the froth for collection.",

    "gravity separation":
        "Gravity separation concentrates minerals based mainly on "
        "differences in density. Examples include shaking tables, "
        "jigs and certain centrifugal concentrators.",

    "magnetic separation":
        "Magnetic separation uses differences in magnetic properties "
        "between minerals to separate magnetic or strongly magnetic "
        "particles from other material.",

    "dewatering":
        "Dewatering removes water from mineral-processing products "
        "such as concentrates or tailings. Equipment can include "
        "thickeners, filters and centrifuges.",

    "concentrate":
        "A concentrate is a product of mineral processing containing "
        "a higher proportion of the valuable mineral or metal than "
        "the original feed.",

    "tailings":
        "Tailings are the materials remaining after valuable minerals "
        "have been separated from the ore during mineral processing. "
        "They require appropriate management and storage.",

    # ========================================================
    # ROCK MECHANICS
    # ========================================================

    "stress":
        "Stress is the internal force per unit cross-sectional area "
        "within a material. Normal stress can be expressed as "
        "Stress = Force / Area.",

    "strain":
        "Strain is the deformation of a material relative to its "
        "original dimension. Normal strain can be expressed as "
        "Strain = Change in Length / Original Length.",

    "young's modulus":
        "Young's modulus describes the relationship between normal "
        "stress and normal strain in the elastic region. "
        "E = Stress / Strain.",

    "youngs modulus":
        "Young's modulus describes the relationship between normal "
        "stress and normal strain in the elastic region. "
        "E = Stress / Strain.",

    "factor of safety":
        "Factor of safety is the ratio between a limiting or failure "
        "strength and the corresponding working or applied stress. "
        "It provides a margin between expected working conditions "
        "and failure conditions.",

    "rock strength":
        "Rock strength describes the ability of rock to resist "
        "failure under applied loading. Common measures include "
        "uniaxial compressive strength and tensile strength.",

    "compressive strength":
        "Compressive strength is the maximum compressive stress that "
        "a material can withstand under specified testing conditions "
        "before failure.",

    "uniaxial compressive strength":
        "Uniaxial compressive strength, or UCS, is the compressive "
        "stress at which a rock specimen fails when subjected to "
        "compression without lateral confining pressure.",

    # ========================================================
    # MINE PLANNING
    # ========================================================

    "mine planning":
        "Mine planning involves determining how a mineral deposit "
        "will be developed and extracted while considering geology, "
        "economics, equipment, production targets, safety and "
        "environmental requirements.",

    "mine life":
        "A simple mine-life estimate is Mine Life = Mineral Reserves / "
        "Annual Production, provided the units are consistent.",

    "mineral reserves":
        "Mineral reserves are economically mineable portions of a "
        "mineral resource, subject to relevant modifying factors such "
        "as mining, processing, economic, legal, environmental and "
        "other considerations.",

    "mineral resource":
        "A mineral resource is a concentration or occurrence of "
        "material of economic interest in or on Earth's crust in "
        "such form and quantity that there are reasonable prospects "
        "for eventual economic extraction, subject to the reporting "
        "standard being used.",

    "cut off grade":
        "Cut-off grade is a grade threshold used to distinguish "
        "material considered for processing or economic extraction "
        "from material considered waste or lower-value material. "
        "The appropriate cut-off depends on technical and economic "
        "conditions.",

    "cutoff grade":
        "Cut-off grade is a grade threshold used to distinguish "
        "material considered for processing or economic extraction "
        "from material considered waste or lower-value material.",

    # ========================================================
    # BLASTING
    # ========================================================

    "powder factor":
        "Powder factor relates explosive quantity to the volume of "
        "rock blasted. A simple expression is "
        "Explosive Mass / Blast Volume.",

    "burden":
        "Burden is the distance from a blast hole to the nearest "
        "free face or, in a blast pattern, the distance between "
        "successive rows of holes measured toward the free face.",

    "spacing":
        "Spacing is the distance between adjacent blast holes along "
        "a row of holes.",

    "stemming":
        "Stemming is inert material placed in the upper part of a "
        "blast hole to help confine explosive gases and energy within "
        "the rock mass.",

    "explosive":
        "An explosive is a material capable of rapidly releasing "
        "energy through a chemical reaction. In mining, explosives "
        "are used for controlled rock fragmentation under designed "
        "and regulated blasting practices.",

    # ========================================================
    # EQUIPMENT
    # ========================================================

    "mining equipment":
        "Mining equipment includes machines used for drilling, "
        "loading, hauling, excavation, dozing, grading, crushing "
        "and other mining activities.",

    "excavator":
        "An excavator is a hydraulic machine commonly used for "
        "digging, loading and material handling. Major components "
        "include the boom, stick, bucket and upper structure.",

    "haul truck":
        "A haul truck is a heavy vehicle used to transport ore, "
        "waste or other materials between locations such as loading "
        "areas, dumps and processing facilities.",

    "loader":
        "A loader is mobile equipment used to load and move material. "
        "In mining, loaders can be used for loading trucks, stockpiling "
        "material and underground mucking.",

    "drill rig":
        "A drill rig is equipment used to create holes in rock for "
        "exploration, production drilling, blasting or other mining "
        "purposes.",

    "bulldozer":
        "A bulldozer is tracked or wheeled equipment fitted with a "
        "blade used for pushing, spreading and grading material.",

    # ========================================================
    # BASIC CALCULATIONS
    # ========================================================

    "density":
        "Density is mass per unit volume. "
        "Density = Mass / Volume.",

    "bulk density":
        "Bulk density is the mass of a material divided by its total "
        "bulk volume, including the spaces between particles.",

    "moisture":
        "Moisture content on a dry basis can be calculated as "
        "(Wet Mass − Dry Mass) / Dry Mass × 100.",

    "haulage":
        "Basic haulage capacity can be estimated from payload and "
        "the number of trips completed. "
        "Trips per hour = 60 / Cycle Time in minutes.",

    "equipment productivity":
        "Basic equipment productivity can be estimated as "
        "Bucket Capacity × Cycles per Hour × Operating Hours.",

    "cut and fill":
        "Cut-and-fill calculations compare material removed from a "
        "cut area with material placed in a fill area. "
        "A simple volume calculation is Area × Depth.",

    "equilibrium":
        "Chemical equilibrium is a dynamic state in which the forward "
        "and reverse reactions occur at equal rates, so the concentrations "
        "of reactants and products remain approximately constant.",

    "gibbs":
        "Gibbs free energy is used to assess the thermodynamic "
        "favorability of a process. At constant temperature and "
        "pressure, a negative change in Gibbs free energy indicates "
        "a thermodynamically favorable direction.",

    "le chatelier":
        "Le Chatelier's principle states that when a system at "
        "equilibrium is disturbed by a change in concentration, "
        "pressure or temperature, the equilibrium shifts in a "
        "direction that tends to oppose the disturbance. In mining "
        "processing, it can help explain chemical equilibria in "
        "processes such as hydrometallurgy.",

    "le chatelier principle":
        "Le Chatelier's principle states that when a system at "
        "equilibrium is disturbed by a change in concentration, "
        "pressure or temperature, the equilibrium shifts in a "
        "direction that tends to oppose the disturbance.",

    "newton":
        "Newton's second law states that the net force acting on "
        "an object equals its mass multiplied by its acceleration: "
        "F = ma."
}


# ============================================================
# LOCAL KNOWLEDGE ANSWER ENGINE
# ============================================================

def ask_ai_fallback(question):
    # Use Cloudflare Workers AI on Render and local Ollama on desktop.
    on_render = os.getenv("RENDER", "").lower() == "true"
    cloudflare_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    cloudflare_api_token = os.getenv("CLOUDFLARE_API_TOKEN")

    if on_render and (
        not cloudflare_account_id or not cloudflare_api_token
    ):
        return None

    try:
        prompt = f"""You are the Mining Engineer Toolkit academic assistant.
Answer clearly for a university student, with a focus on mining
engineering, geology, mineral processing, and related engineering topics.

Answer the question directly and keep the explanation concise. When a
student asks for an example, give one concrete, realistic mining example
that directly illustrates the topic they asked about. If the question is
a follow-up, answer that follow-up using the previous student question;
do not repeat the previous answer, output conversation labels, or give
unrelated examples. For emerging technologies, distinguish proposed or
research applications from established real-world use. Do not claim a
technology is faster or better in general; explain that performance
depends on the specific task and available technology. When explaining
quantum computing, do not say that superposition simply processes many
answers at once. Explain that measurement produces an outcome and that
quantum algorithms use interference; any speedup applies only to certain
problems. Note that current quantum hardware has practical limitations.
Avoid formulas
unless the student asks for one. If a formula is requested, explain it
in plain words and use words such as "times" and "divided by" instead of
symbols such as an asterisk. Never use LaTeX, backslash commands, or
Markdown styling such as bold text. If a question is outside mining
engineering, say so briefly and still answer it accurately. Do not
invent data or present a general explanation as a site-specific mine
design recommendation.

Student question:
{question}
"""

        if on_render:
            response = requests.post(
                "https://api.cloudflare.com/client/v4/accounts/"
                f"{cloudflare_account_id}/ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {cloudflare_api_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": os.getenv(
                        "CLOUDFLARE_MODEL",
                        "@cf/qwen/qwen3.8-27b"
                    ),
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "max_tokens": 1200
                },
                timeout=300
            )
        else:
            response = requests.post(
                os.getenv(
                    "OLLAMA_URL",
                    "http://localhost:11434/api/generate"
                ),
                json={
                    "model": os.getenv("OLLAMA_LOCAL_MODEL", "qwen2.5:3b"),
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300
            )

        response.raise_for_status()

        data = response.json()

        if on_render:
            choices = data.get("choices", [])
            if choices:
                return (
                    choices[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
            return ""

        return data.get("response", "").strip()

    except requests.exceptions.RequestException:
        return None

def find_local_answer(question):

    q = question.lower().strip()

    # --------------------------------------------------------
    # CLEAN COMMON WORDING
    # --------------------------------------------------------

    q = q.replace("what's", "what is")
    q = q.replace("whats", "what is")
    q = q.replace("pls", "please")
    q = q.replace("pls.", "please")
    q = q.replace("open-pit", "open pit")

    if "example" in q and "open pit mining" in q:
        return (
            "Imagine a copper deposit lies close to the surface. The mine "
            "removes the soil and waste rock above it, then extracts the "
            "ore in a series of wide steps called benches. Haul trucks carry "
            "the ore to a crusher, while waste rock is taken to a dump. "
            "That is a simplified example of open-pit mining."
        )

    # These are application questions, not requests for a basic
    # equipment definition. Let them fall through to the AI fallback.
    if any(phrase in q for phrase in (
        "machine learning",
        "artificial intelligence",
        "predictive maintenance",
        "neural network",
        "deep learning",
    )):
        return None

    # --------------------------------------------------------
    # OPEN PIT VS UNDERGROUND
    # --------------------------------------------------------

    if (
        ("open-pit" in q or "open pit" in q)
        and "underground" in q
    ):
        return (
            "Open-pit mining extracts ore from near the surface by "
            "removing overburden and waste in a series of benches. "
            "It is commonly suited to deposits that are relatively "
            "close to the surface and can be mined economically by "
            "surface methods.\n\n"
            "Underground mining extracts ore below the surface using "
            "workings such as shafts, declines, ramps, drifts, "
            "crosscuts and raises. It is commonly considered when "
            "the deposit is deep or when removing the overlying "
            "material by surface methods would not be suitable.\n\n"
            "The choice depends on factors such as deposit geometry, "
            "depth, grade, rock conditions, production requirements, "
            "cost and environmental considerations."
        )

    # --------------------------------------------------------
    # SURFACE VS UNDERGROUND
    # --------------------------------------------------------

    if (
        ("surface mining" in q)
        and ("underground mining" in q or "underground" in q)
    ):
        return (
            "Surface mining extracts material from near the surface "
            "using methods such as open-pit mining. It normally "
            "involves removing overburden and waste to access the ore.\n\n"
            "Underground mining accesses deeper deposits through "
            "workings such as shafts, declines and tunnels. The "
            "method selected depends on the deposit, ground conditions, "
            "economics, production requirements and other constraints."
        )

    # --------------------------------------------------------
    # SPECIFIC LE CHATELIER
    # --------------------------------------------------------

    if (
        "le chatelier" in q
        or "le chatelier's principle" in q
        or "le chatelier principle" in q
    ):
        return LOCAL_KNOWLEDGE["le chatelier principle"]

    # --------------------------------------------------------
    # SPECIFIC FORMULA QUESTIONS
    # --------------------------------------------------------

    if "formula" in q and "stripping ratio" in q:
        return (
            "The stripping ratio formula is:\n\n"
            "Stripping Ratio = Overburden / Ore.\n\n"
            "It compares the amount of waste material removed with "
            "the amount of ore obtained."
        )

    if "formula" in q and "porosity" in q:
        return (
            "The porosity formula is:\n\n"
            "Porosity = (Pore Volume / Total Volume) × 100.\n\n"
            "It gives the percentage of the total rock or soil volume "
            "occupied by void spaces."
        )

    if (
        "formula" in q
        and "density" in q
        and "bulk density" not in q
    ):
        return (
            "The basic density formula is:\n\n"
            "Density = Mass / Volume.\n\n"
            "A common SI unit is kg/m³."
        )

    if "formula" in q and "recovery" in q:
        return (
            "The recovery formula is:\n\n"
            "Recovery = (Recovered Metal / Available Metal) × 100."
        )

    if "formula" in q and "mine life" in q:
        return (
            "A simple mine-life formula is:\n\n"
            "Mine Life = Mineral Reserves / Annual Production.\n\n"
            "Make sure both quantities use compatible units."
        )

    # --------------------------------------------------------
    # DEFINITIONS
    # --------------------------------------------------------

    if "what is mining" in q:
        return LOCAL_KNOWLEDGE["what is mining"]

    if "define mining" in q:
        return LOCAL_KNOWLEDGE["what is mining"]

    # --------------------------------------------------------
    # TOPIC KNOWLEDGE
    # --------------------------------------------------------

    topic_answer = find_topic_answer(q)

    if topic_answer:
        return topic_answer

    # --------------------------------------------------------
    # QUESTION PATTERNS
    # --------------------------------------------------------

    question_patterns = [
        ("what is", "define"),
        ("what are", "define"),
        ("define", "define"),
        ("explain", "explain"),
        ("tell me about", "explain"),
        ("meaning of", "define"),
        ("meaning", "define"),
    ]

    cleaned_question = q

    for phrase, replacement in question_patterns:
        cleaned_question = cleaned_question.replace(
            phrase,
            ""
        )

    # --------------------------------------------------------
    # MORE SPECIFIC TERMS FIRST
    # --------------------------------------------------------

    keywords = sorted(
        LOCAL_KNOWLEDGE.keys(),
        key=len,
        reverse=True
    )

    for keyword in keywords:

        if keyword in cleaned_question or keyword in q:

            return LOCAL_KNOWLEDGE[keyword]

    # --------------------------------------------------------
    # GENERAL MINING RESPONSE
    # --------------------------------------------------------

    if "mining engineering" in q:
        return (
            "Mining engineering is the engineering discipline "
            "concerned with the exploration, planning, design, "
            "operation and management of mines and the extraction "
            "of mineral resources. It combines areas such as "
            "geology, rock mechanics, mine planning, mineral "
            "processing, equipment, blasting, surveying and "
            "environmental management."
        )

    return None


# ============================================================
# AI ASSISTANT
# ============================================================

@app.route("/ai-assistant", methods=["GET", "POST"])
def ai_assistant():

    # ========================================================
    # GET REQUEST
    # ========================================================

    if request.method == "GET":

        requested_chat_id = request.args.get(
            "conversation_id"
        )

        chat_id = valid_chat_id(requested_chat_id)

        if not chat_id or not get_chat(chat_id):

            chat_id = create_chat("New Chat")

            return redirect(
                url_for(
                    "ai_assistant",
                    conversation_id=chat_id
                )
            )

        conversations = get_chats()
        messages = get_messages(chat_id)
        conversation = get_chat(chat_id)

        return render_template(
            "ai_assistant.html",
            conversations=conversations,
            messages=messages,
            conversation_id=chat_id,
            conversation=conversation,
            answer=None
        )

    # ========================================================
    # POST REQUEST
    # ========================================================

    question = request.form.get(
        "question",
        ""
    ).strip()

    requested_chat_id = request.form.get(
        "conversation_id"
    )

    chat_id = valid_chat_id(requested_chat_id)

    if not chat_id or not get_chat(chat_id):

        chat_id = create_chat("New Chat")

    # --------------------------------------------------------
    # Empty question
    # --------------------------------------------------------

    if not question:

        conversations = get_chats()
        messages = get_messages(chat_id)
        conversation = get_chat(chat_id)

        return render_template(
            "ai_assistant.html",
            conversations=conversations,
            messages=messages,
            conversation_id=chat_id,
            conversation=conversation,
            answer="Please enter a question."
        )

    # --------------------------------------------------------
    # If this is the first message, create a useful title.
    # --------------------------------------------------------

    existing_messages = get_messages(chat_id)

    if not existing_messages:

        title = make_chat_title(question)

        import sqlite3

        connection = sqlite3.connect(
            "chat_history.db"
        )

        connection.execute(
            """
            UPDATE chats
            SET title = ?
            WHERE id = ?
            """,
            (title, chat_id)
        )

        connection.commit()
        connection.close()

    # --------------------------------------------------------
    # SAVE USER MESSAGE
    # --------------------------------------------------------

    add_message(
        chat_id,
        "user",
        question
    )

    # --------------------------------------------------------
    # STEP 1:
    # Try local Mining Engineer Toolkit knowledge first.
    # Use conversation context for follow-up questions.
    # --------------------------------------------------------

    local_question = contextual_question(
        chat_id,
        question
    )

    local_answer = find_local_answer(
        local_question
    )

    if local_answer:

        answer = local_answer

        add_message(
            chat_id,
            "assistant",
            answer
        )

        return redirect(
            url_for(
                "ai_assistant",
                conversation_id=chat_id
            )
        )
    # --------------------------------------------------------
    # STEP 2:
    # If the Toolkit does not know the answer,
    # ask Cloudflare Workers AI on Render or local Ollama on desktop.
    # --------------------------------------------------------

    ai_answer = ask_ai_fallback(
        local_question
    )

    if ai_answer:

        answer = ai_answer

        add_message(
            chat_id,
            "assistant",
            answer
        )

        return redirect(
            url_for(
                "ai_assistant",
                conversation_id=chat_id
            )
        )
    # Do not depend on Gemini when hosted inference is unavailable.
    if os.getenv("RENDER", "").lower() == "true":
        answer = (
            "Cloudflare Workers AI could not answer this question. Check "
            "that CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are set "
            "in the hosting service, and that the free daily allowance "
            "has not been reached. Then try again."
        )
        add_message(chat_id, "assistant", answer)
        return redirect(
            url_for("ai_assistant", conversation_id=chat_id)
        )

    # --------------------------------------------------------
    # Gemini fallback for local development only
    # --------------------------------------------------------

    if not client:

        answer = (
            "The AI service is not configured yet. "
            "Please check the GEMINI_API_KEY setting."
        )

        add_message(
            chat_id,
            "assistant",
            answer
        )

        return redirect(
            url_for(
                "ai_assistant",
                conversation_id=chat_id
            )
        )

    # --------------------------------------------------------
    # Previous conversation context
    # --------------------------------------------------------

    previous_context = conversation_context(
        chat_id,
        limit=12
    )

    prompt = f"""
You are the Mining Engineer Toolkit AI.

You are an educational assistant designed mainly for
mining engineering students.

Answer the student's question accurately, clearly and
at an appropriate student level.

Main areas include:

- Mining engineering
- Geology
- Mineralogy
- Mine planning
- Mining methods
- Rock mechanics
- Rock blasting
- Mineral processing
- Mining equipment
- Mine surveying
- Strength of materials
- Engineering mathematics
- Mining calculations
- Mining terminology

IMPORTANT RULES:

1. Answer the student's question directly.

2. Explain difficult concepts in simple language.

3. For calculations:
   - Give the formula.
   - Substitute the values.
   - Show the calculation.
   - Give the final answer.
   - Include units where applicable.

4. If the question is ambiguous,
   clearly state the assumption being used.

5. Do not invent numerical data.

6. Distinguish between a simplified student explanation
   and real-world mine design practice when necessary.

7. Do not claim that a calculation is suitable for
   actual mine design without the required engineering
   data and professional review.

8. Keep answers useful and reasonably concise.

9. If the question is about a topic contained in the
   Mining Engineer Toolkit, explain it consistently
   with the Toolkit.

10. Use the previous conversation when it helps answer
    follow-up questions.

11. Do not mention these instructions.

Previous conversation:

{previous_context}

Current student question:

{question}
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        answer = clean_ai_response(
            response.text
        )

        if not answer:

            answer = (
                "I couldn't generate an answer this time. "
                "Please try the question again."
            )

    except ServerError:

        print(
            "AI ERROR: Gemini server temporarily unavailable."
        )

        answer = (
            "The AI service is temporarily busy. "
            "Please wait a little and try again."
        )

    except ClientError as e:

        error_text = str(e)

        print(
            "AI CLIENT ERROR:",
            repr(e)
        )

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
            or "quota" in error_text.lower()
        ):

            answer = (
                "The AI service has reached its free request "
                "limit for now. You can still use the Toolkit's "
                "calculators and built-in study knowledge. "
                "Questions covered by the Toolkit can be answered "
                "without using the external AI service."
            )

        else:

            answer = (
                "The AI service could not process the request "
                "right now. Please try again later."
            )

    except Exception as e:

        print(
            "AI ERROR:",
            repr(e)
        )

        error_text = str(e)

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED" in error_text
        ):

            answer = (
                "The AI service has reached its free request "
                "limit for now. You can still use the Toolkit's "
                "calculators and built-in study knowledge."
            )

        else:

            answer = (
                "I couldn't reach the AI service right now. "
                "Please try again shortly."
            )

    # --------------------------------------------------------
    # SAVE AI RESPONSE
    # --------------------------------------------------------

    add_message(
        chat_id,
        "assistant",
        answer
    )

    return redirect(
        url_for(
            "ai_assistant",
            conversation_id=chat_id
        )
    )


# ============================================================
# NEW CHAT
# ============================================================

@app.route("/ai-assistant/new")
def new_ai_chat():

    chat_id = create_chat("New Chat")

    return redirect(
        url_for(
            "ai_assistant",
            conversation_id=chat_id
        )
    )


# ============================================================
# DELETE CHAT
# ============================================================

@app.route(
    "/ai-assistant/delete/<int:chat_id>",
    methods=["POST"]
)
def delete_ai_chat(chat_id):

    delete_chat(chat_id)

    return redirect(
        url_for("ai_assistant")
    )


# ============================================================
# RENAME CHAT
# ============================================================

@app.route(
    "/ai-assistant/rename/<int:chat_id>",
    methods=["POST"]
)
def rename_ai_chat(chat_id):

    new_title = request.form.get(
        "title",
        ""
    ).strip()

    if new_title:

        if len(new_title) > 60:
            new_title = new_title[:60].rstrip() + "..."

        import sqlite3

        connection = sqlite3.connect(
            "chat_history.db"
        )

        connection.execute(
            """
            UPDATE chats
            SET title = ?
            WHERE id = ?
            """,
            (new_title, chat_id)
        )

        connection.commit()
        connection.close()

    return redirect(
        url_for(
            "ai_assistant",
            conversation_id=chat_id
        )
    )


# ============================================================
# START FLASK
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        debug=True,
        port=int(
            os.environ.get(
                "PORT",
                5001
            )
        )
    )
