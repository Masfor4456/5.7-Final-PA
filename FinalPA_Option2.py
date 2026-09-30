"""
Name: Mason Ford
Date: September 30, 2026
Selected Option: Option 2 - Column Family Database

Summary:
    This Python program uses Apache Cassandra to perform CRUD operations
    on the FinalPA review dataset. The program provides a menu-driven
    interface for inserting, reading, updating/deleting as required,
    searching review information, counting reviews by category and star
    rating, and deleting the ReviewData and ProductData tables.

    For Option 2, title and body searches use the Cassandra equality (=)
    operator rather than a regular-expression search.
"""

import json
from pathlib import Path

from cassandra.cluster import Cluster
from cassandra.query import PreparedStatement


# ----------------------------- Configuration -----------------------------

KEYSPACE = "final_pa"
REVIEW_TABLE = '"ReviewData"'
PRODUCT_TABLE = '"ProductData"'
DATASET_FILE = Path(__file__).with_name("FinalPA-Dataset.json")

# Change this only if Cassandra is running somewhere other than localhost.
CASSANDRA_HOST = "127.0.0.1"
CASSANDRA_PORT = 9042


# ----------------------------- Database Setup -----------------------------

def connect_to_cassandra():
    """Connect to Cassandra and return the cluster and session."""
    cluster = Cluster([CASSANDRA_HOST], port=CASSANDRA_PORT)
    session = cluster.connect()

    session.execute(
        f"""
        CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """
    )

    session.set_keyspace(KEYSPACE)
    return cluster, session


def create_tables(session):
    """Create the ReviewData and ProductData column-family tables."""
    session.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {REVIEW_TABLE} (
            review_id text PRIMARY KEY,
            product_id text,
            reviewer_id text,
            stars int,
            review_body text,
            review_title text,
            language text,
            product_category text
        )
        """
    )

    session.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {PRODUCT_TABLE} (
            product_id text PRIMARY KEY,
            product_category text
        )
        """
    )


# ----------------------------- Dataset Loading -----------------------------

def dataset_is_loaded(session):
    """Return True if ReviewData already contains records."""
    row = session.execute(
        f"SELECT COUNT(*) FROM {REVIEW_TABLE}"
    ).one()
    return row.count > 0


def load_dataset(session):
    """
    Load FinalPA-Dataset.json into ReviewData and ProductData.

    The supplied dataset contains 5,000 review records. ProductData is
    built from the unique product_id/product_category combinations present
    in the supplied review dataset.
    """
    if not DATASET_FILE.exists():
        print(f"\nDataset not found: {DATASET_FILE}")
        print("Place FinalPA-Dataset.json in the same folder as this program.")
        return

    if dataset_is_loaded(session):
        print("\nReviewData already contains data. Dataset loading skipped.")
        return

    insert_review = session.prepare(
        f"""
        INSERT INTO {REVIEW_TABLE}
        (review_id, product_id, reviewer_id, stars, review_body,
         review_title, language, product_category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )

    insert_product = session.prepare(
        f"""
        INSERT INTO {PRODUCT_TABLE}
        (product_id, product_category)
        VALUES (?, ?)
        """
    )

    products = {}

    print("\nLoading FinalPA-Dataset.json...")

    with DATASET_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue

            record = json.loads(line)

            session.execute(
                insert_review,
                (
                    record["review_id"],
                    record["product_id"],
                    record["reviewer_id"],
                    int(record["stars"]),
                    record["review_body"],
                    record["review_title"],
                    record["language"],
                    record["product_category"],
                ),
            )

            products[record["product_id"]] = record["product_category"]

            if line_number % 500 == 0:
                print(f"  Loaded {line_number} review records...")

    for product_id, category in products.items():
        session.execute(insert_product, (product_id, category))

    print(f"Dataset loaded: {line_number} review records.")
    print(f"ProductData loaded: {len(products)} unique products.")


# ----------------------------- CRUD Operations -----------------------------

def insert_review(session):
    """Insert a new review into ReviewData."""
    print("\n--- Insert New Review ---")

    review_id = input("Review ID: ").strip()
    product_id = input("Product ID: ").strip()
    reviewer_id = input("Reviewer ID: ").strip()

    while True:
        try:
            stars = int(input("Stars (1-5): ").strip())
            if 1 <= stars <= 5:
                break
            print("Stars must be between 1 and 5.")
        except ValueError:
            print("Please enter a whole number.")

    review_body = input("Review body: ").strip()
    review_title = input("Review title: ").strip()
    language = input("Language: ").strip()
    product_category = input("Product category: ").strip()

    session.execute(
        f"""
        INSERT INTO {REVIEW_TABLE}
        (review_id, product_id, reviewer_id, stars, review_body,
         review_title, language, product_category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            review_id,
            product_id,
            reviewer_id,
            stars,
            review_body,
            review_title,
            language,
            product_category,
        ),
    )

    print("Review inserted successfully.")


def insert_product(session):
    """Insert a new product into ProductData."""
    print("\n--- Insert New Product ---")

    product_id = input("Product ID: ").strip()
    product_category = input("Product category: ").strip()

    session.execute(
        f"""
        INSERT INTO {PRODUCT_TABLE}
        (product_id, product_category)
        VALUES (?, ?)
        """,
        (product_id, product_category),
    )

    print("Product inserted successfully.")


def display_review_by_id(session):
    """Display all information associated with a user-entered review_id."""
    print("\n--- Find Review by Review ID ---")

    review_id = input("Enter review_id: ").strip()

    row = session.execute(
        f"SELECT * FROM {REVIEW_TABLE} WHERE review_id = %s",
        (review_id,),
    ).one()

    if row is None:
        print("No review found with that review_id.")
        return

    print("\nReview Information")
    print(f"Review ID:        {row.review_id}")
    print(f"Product ID:       {row.product_id}")
    print(f"Reviewer ID:      {row.reviewer_id}")
    print(f"Stars:            {row.stars}")
    print(f"Review Title:     {row.review_title}")
    print(f"Review Body:      {row.review_body}")
    print(f"Language:         {row.language}")
    print(f"Product Category: {row.product_category}")


def display_categories(session):
    """Display all distinct product categories."""
    print("\n--- Distinct Product Categories ---")

    rows = session.execute(
        f"SELECT product_category FROM {PRODUCT_TABLE}"
    )

    categories = sorted(
        {row.product_category for row in rows if row.product_category}
    )

    if not categories:
        print("No product categories found.")
        return

    for category in categories:
        print(category)

    print(f"\nTotal distinct categories: {len(categories)}")


def count_star_reviews(session, minimum_star, maximum_star):
    """Count reviews within a selected star range for a category."""
    category = input("Enter product category: ").strip()

    rows = session.execute(
        f"""
        SELECT stars
        FROM {REVIEW_TABLE}
        WHERE product_category = %s
        ALLOW FILTERING
        """,
        (category,),
    )

    count = sum(
        1 for row in rows
        if minimum_star <= row.stars <= maximum_star
    )

    print(
        f"\nNumber of {minimum_star}- and {maximum_star}-star reviews "
        f"for '{category}': {count}"
    )


def search_review_title(session):
    """
    Search for reviews whose title exactly equals user-entered content.

    Option 2 requires the Equals operator. The CQL query therefore uses:
        WHERE review_title = ?
    """
    print("\n--- Search Review Title ---")
    title = input("Enter the exact review title: ").strip()

    rows = session.execute(
        f"""
        SELECT *
        FROM {REVIEW_TABLE}
        WHERE review_title = %s
        ALLOW FILTERING
        """,
        (title,),
    )

    display_search_results(rows, "review title")


def search_review_body(session):
    """
    Search for reviews whose body exactly equals user-entered content.

    Option 2 requires the Equals operator. The CQL query therefore uses:
        WHERE review_body = ?
    """
    print("\n--- Search Review Body ---")
    body = input("Enter the exact review body: ").strip()

    rows = session.execute(
        f"""
        SELECT *
        FROM {REVIEW_TABLE}
        WHERE review_body = %s
        ALLOW FILTERING
        """,
        (body,),
    )

    display_search_results(rows, "review body")


def display_search_results(rows, search_type):
    """Display results returned from an exact title/body search."""
    found = False

    for row in rows:
        found = True
        print("\n------------------------------")
        print(f"Review ID:        {row.review_id}")
        print(f"Product ID:       {row.product_id}")
        print(f"Reviewer ID:      {row.reviewer_id}")
        print(f"Stars:            {row.stars}")
        print(f"Review Title:     {row.review_title}")
        print(f"Review Body:      {row.review_body}")
        print(f"Language:         {row.language}")
        print(f"Product Category: {row.product_category}")

    if not found:
        print(f"No reviews found with that exact {search_type}.")


def delete_review(session):
    """Delete one review from ReviewData."""
    print("\n--- Delete Review ---")

    review_id = input("Enter review_id to delete: ").strip()

    row = session.execute(
        f"SELECT review_id FROM {REVIEW_TABLE} WHERE review_id = %s",
        (review_id,),
    ).one()

    if row is None:
        print("No review found with that review_id.")
        return

    confirm = input(
        f"Delete review '{review_id}'? (y/n): "
    ).strip().lower()

    if confirm == "y":
        session.execute(
            f"DELETE FROM {REVIEW_TABLE} WHERE review_id = %s",
            (review_id,),
        )
        print("Review deleted successfully.")
    else:
        print("Delete cancelled.")


# ----------------------------- Table Deletion -----------------------------

def delete_review_data(session):
    """Delete the ReviewData table."""
    confirm = input(
        "\nThis will delete the entire ReviewData table. Continue? (y/n): "
    ).strip().lower()

    if confirm == "y":
        session.execute(f"DROP TABLE IF EXISTS {REVIEW_TABLE}")
        print("ReviewData has been deleted.")
        print("Exit the program after this operation.")
    else:
        print("Delete cancelled.")


def delete_product_data(session):
    """Delete the ProductData table."""
    confirm = input(
        "\nThis will delete the entire ProductData table. Continue? (y/n): "
    ).strip().lower()

    if confirm == "y":
        session.execute(f"DROP TABLE IF EXISTS {PRODUCT_TABLE}")
        print("ProductData has been deleted.")
        print("Exit the program after this operation.")
    else:
        print("Delete cancelled.")


# ----------------------------- Menu -----------------------------

def display_menu():
    """Display the main menu."""
    print("\n" + "=" * 55)
    print("     FINAL PROJECT - OPTION 2: COLUMN FAMILY DB")
    print("=" * 55)
    print("1. Insert new ReviewData")
    print("2. Insert new ProductData")
    print("3. Display information by review_id")
    print("4. Display all distinct product categories")
    print("5. Count 4- and 5-star reviews by category")
    print("6. Count 1- and 2-star reviews by category")
    print("7. Search reviews by exact title")
    print("8. Search reviews by exact body")
    print("9. Delete a review")
    print("10. Delete ReviewData")
    print("11. Delete ProductData")
    print("0. Exit")
    print("=" * 55)


def main():
    cluster = None
    session = None

    try:
        cluster, session = connect_to_cassandra()
        create_tables(session)

        print("Connected to Cassandra successfully.")

        # Automatically load the supplied assignment dataset the first
        # time the program is run.
        load_dataset(session)

        while True:
            display_menu()
            choice = input("Enter your choice: ").strip()

            try:
                if choice == "1":
                    insert_review(session)

                elif choice == "2":
                    insert_product(session)

                elif choice == "3":
                    display_review_by_id(session)

                elif choice == "4":
                    display_categories(session)

                elif choice == "5":
                    count_star_reviews(session, 4, 5)

                elif choice == "6":
                    count_star_reviews(session, 1, 2)

                elif choice == "7":
                    search_review_title(session)

                elif choice == "8":
                    search_review_body(session)

                elif choice == "9":
                    delete_review(session)

                elif choice == "10":
                    delete_review_data(session)

                elif choice == "11":
                    delete_product_data(session)

                elif choice == "0":
                    print("\nExiting program.")
                    break

                else:
                    print("Invalid choice. Please select a menu option.")

            except Exception as error:
                print(f"\nOperation failed: {error}")

    except Exception as error:
        print("\nUnable to connect to Cassandra.")
        print(f"Error: {error}")
        print(
            "Make sure Cassandra is running and listening on "
            f"{CASSANDRA_HOST}:{CASSANDRA_PORT}."
        )

    finally:
        if session is not None:
            session.shutdown()
        if cluster is not None:
            cluster.shutdown()


if __name__ == "__main__":
    main()
