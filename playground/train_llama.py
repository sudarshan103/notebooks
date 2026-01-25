import json, random, sys

QUANTITIES = [250, 500, 1000]
COMPLAINT_TYPES_LOW = []
COMPLAINT_TYPES_MED = ["delivery delay", "refund delay"]
COMPLAINT_TYPES_HIGH = ["milk quality issue", "product defect", "refund delay", "multiple issues"]

ACTIONS = {
    1: "Maintain engagement with loyalty rewards or appreciation message.",
    2: "Offer moderate loyalty credits or targeted discounts to prevent churn.",
    3: "Immediate outreach from support with personalized discount or offer."
}

TOTAL_RECORDS = 20000
DISTRIBUTION = {1: 0.3, 2: 0.4, 3: 0.3}
TARGET_COUNTS = {score: int(TOTAL_RECORDS * frac) for score, frac in DISTRIBUTION.items()}

def generate_customer_record(churn_score: int):
    quantity = random.choice(QUANTITIES)
    if churn_score == 1:
        duration_months = random.randint(5, 8)
        price_hike = random.choice([0, 3, 5])
        complaints = 0
        complaint_type = None
        last_purchase_gap = random.randint(0, 15)
        competitor_price_drop = False
        regularity = "regularly"
    elif churn_score == 2:
        duration_months = random.randint(3, 6)
        price_hike = random.randint(8, 12)
        complaints = random.choice([1, 2])
        complaint_type = random.choice(COMPLAINT_TYPES_MED)
        last_purchase_gap = random.randint(16, 30)
        competitor_price_drop = random.random() < 0.2
        regularity = random.choice(["regularly", "slightly irregularly"])
    else:  # churn_score == 3
        duration_months = random.randint(1, 4)
        price_hike = random.randint(13, 20)
        complaints = random.randint(2, 3)
        complaint_type = random.choice(COMPLAINT_TYPES_HIGH)
        last_purchase_gap = random.randint(31, 45)
        competitor_price_drop = random.random() < 0.6
        regularity = "irregularly"

    # Build description
    profile = f"Customer bought {quantity}ml {regularity} for {duration_months} months. "
    profile += f"Price increased by {price_hike}% recently. "
    if complaints > 0:
        profile += f"They raised {complaints} complaint(s) about {complaint_type}. "
    else:
        profile += "No complaints have been raised. "
    profile += f"Last purchase was {last_purchase_gap} days ago. "
    if competitor_price_drop:
        profile += "Competitor has reduced their prices recently."

    # Reasoning
    if churn_score == 1:
        reasoning = "Stable purchasing pattern, minimal price impact, and no complaints."
    elif churn_score == 2:
        reasoning = "Moderate churn risk due to noticeable price increase or minor service issues."
    else:
        reasoning = "High churn risk due to inactivity, major complaints, and strong competitor offers."

    question = f"{profile.strip()} Predict churn risk."
    answer = f"Churn Score: {churn_score}\nReasoning: {reasoning}\nAction: {ACTIONS[churn_score]}"

    return {"question": question, "answer": answer}


def generate_dataset(filename="churn_dataset_v2.jsonl", show_progress=True):
    counter = {1: 0, 2: 0, 3: 0}
    total = 0
    with open(filename, "w", encoding="utf-8") as f:
        while total < TOTAL_RECORDS:
            for score in [1, 2, 3]:
                if counter[score] < TARGET_COUNTS[score]:
                    record = generate_customer_record(score)
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    counter[score] += 1
                    total += 1
                    if show_progress and total % 1000 == 0:
                        sys.stdout.write(f"\rProgress: {total}/{TOTAL_RECORDS}")
                        sys.stdout.flush()
                    if total >= TOTAL_RECORDS:
                        break
    print(f"\n✅ Generated {TOTAL_RECORDS} records with distribution {counter}")

if __name__ == "__main__":
    generate_dataset()
