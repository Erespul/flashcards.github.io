"""
Math Flash Cards Website - Main Application
A Flask-based web application for creating and practicing math flashcards.
Uses CSV files for data storage (users and flashcards).
"""

# Flask imports - web framework for handling HTTP requests and rendering templates
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
# CSV module - for reading/writing CSV files (user and flashcard data)
import csv
# OS module - for file system operations (checking if files exist)
import os
# Datetime module - for timestamp generation when creating records
from datetime import datetime

# Increase CSV field size limit to handle large base64-encoded images
# Default limit is 131072 bytes (128KB), which is too small for images
# Setting to 10MB (10 * 1024 * 1024) should be sufficient for most images
csv.field_size_limit(10 * 1024 * 1024)  # 10MB limit

# Initialize Flask application
app = Flask(__name__)
# Secret key required for Flask sessions and flash messages
# In production, this should be a secure random string stored in environment variables
app.secret_key = 'your-secret-key-here'  # Required for flash messages and sessions

# CSV file paths - constants for data storage files
USERS_CSV = 'users.csv'  # Stores user account information
FLASHCARDS_CSV = 'flashcards.csv'  # Stores all flashcard data

# ============================================================================
# CSV Initialization Functions
# ============================================================================

def init_users_csv():
    """
    Initialize the users CSV file with headers if it doesn't exist.
    Creates a new CSV file with columns: name, email, password, created_at
    """
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['name', 'email', 'password', 'created_at'])

def init_flashcards_csv():
    """
    Initialize the flashcards CSV file with headers if it doesn't exist.
    Creates a new CSV file with columns: id, user_email, name, question, answer, image_question, image_answer, collection, created_at
    """
    if not os.path.exists(FLASHCARDS_CSV):
        with open(FLASHCARDS_CSV, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['id', 'user_email', 'name', 'question', 'answer', 'image_question', 'image_answer', 'collection', 'created_at'])

def migrate_flashcards_csv():
    """
    Migrate old flashcards.csv format to new format with id, collection, and name columns.
    This function handles backward compatibility for existing data.
    - Checks if migration is needed by examining the header row
    - Backs up the old file before migration
    - Assigns sequential IDs to existing cards
    - Sets empty collection and name for old cards
    """
    if not os.path.exists(FLASHCARDS_CSV):
        return
    
    # Read the current file to check if migration is needed
    with open(FLASHCARDS_CSV, 'r', newline='', encoding='utf-8') as file:
        first_line = file.readline().strip()
        # Check if already has all required columns including images
        if 'id' in first_line and 'collection' in first_line and 'name' in first_line and 'image_question' in first_line:
            return  # Already migrated - no action needed
    
    # Backup the old file before migration
    backup_file = FLASHCARDS_CSV + '.backup'
    if os.path.exists(backup_file):
        # If backup already exists, use a timestamped backup
        import time
        backup_file = FLASHCARDS_CSV + '.backup.' + str(int(time.time()))
    os.rename(FLASHCARDS_CSV, backup_file)
    
    # Read old format and write new format
    migrated_cards = []
    with open(backup_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        # Enumerate starts at 1 to assign IDs starting from 1
        for i, row in enumerate(reader, 1):
            migrated_cards.append({
                'id': i,
                'user_email': row['user_email'],
                'name': row.get('name', ''),  # Empty name for old cards (backward compatibility)
                'question': row['question'],
                'answer': row['answer'],
                'image_question': row.get('image_question', ''),  # Empty image for old cards
                'image_answer': row.get('image_answer', ''),  # Empty image for old cards
                'collection': row.get('collection', ''),  # Empty collection for old cards if not present
                'created_at': row['created_at']
            })
    
    # Write new format with all required columns
    with open(FLASHCARDS_CSV, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'user_email', 'name', 'question', 'answer', 'image_question', 'image_answer', 'collection', 'created_at'])
        for card in migrated_cards:
            writer.writerow([card['id'], card['user_email'], card['name'], card['question'], card['answer'], card['image_question'], card['image_answer'], card['collection'], card['created_at']])

# ============================================================================
# User Management Functions
# ============================================================================

def save_user_to_csv(name, email, password):
    """
    Save user registration data to CSV file.
    Args:
        name: User's full name
        email: User's email address (used as unique identifier)
        password: User's password (stored in plain text - not secure for production)
    """
    # Generate timestamp for when the account was created
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(USERS_CSV, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([name, email, password, created_at])

def email_exists(email):
    """
    Check if email already exists in the CSV file.
    Used during registration to prevent duplicate accounts.
    Args:
        email: Email address to check
    Returns:
        True if email exists, False otherwise
    """
    if not os.path.exists(USERS_CSV):
        return False
    
    # Case-insensitive email comparison
    with open(USERS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['email'].lower() == email.lower():
                return True
    return False

def verify_user(email, password):
    """
    Verify user credentials and return user data if valid.
    Used during login to authenticate users.
    Args:
        email: User's email address
        password: User's password
    Returns:
        Dictionary with user data if credentials are valid, None otherwise
    """
    if not os.path.exists(USERS_CSV):
        return None
    
    # Case-insensitive email comparison, exact password match
    with open(USERS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['email'].lower() == email.lower() and row['password'] == password:
                # Return user data (excluding password for security)
                return {
                    'name': row['name'],
                    'email': row['email'],
                    'created_at': row['created_at']
                }
    return None

# ============================================================================
# Flashcard Management Functions
# ============================================================================

def get_next_flashcard_id():
    """
    Get the next available flashcard ID by finding the maximum existing ID.
    Returns:
        Next available ID (max_id + 1), or 1 if no flashcards exist
    """
    if not os.path.exists(FLASHCARDS_CSV):
        return 1
    
    max_id = 0
    with open(FLASHCARDS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                # Convert ID to integer and track the maximum
                card_id = int(row.get('id', 0))
                max_id = max(max_id, card_id)
            except ValueError:
                # Skip rows with invalid ID format
                continue
    return max_id + 1

def get_user_flashcards(user_email):
    """
    Get all flashcards for a specific user.
    Args:
        user_email: Email of the user whose flashcards to retrieve
    Returns:
        List of flashcard dictionaries, empty list if none exist
    """
    if not os.path.exists(FLASHCARDS_CSV):
        return []
    
    flashcards = []
    with open(FLASHCARDS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Case-insensitive email matching
            if row['user_email'].lower() == user_email.lower():
                flashcards.append({
                    'id': row['id'],
                    'name': row.get('name', ''),  # Default to empty string if missing
                    'question': row['question'],
                    'answer': row['answer'],
                    'image_question': row.get('image_question', ''),  # Default to empty string if missing
                    'image_answer': row.get('image_answer', ''),  # Default to empty string if missing
                    'collection': row.get('collection', ''),  # Default to empty string if missing
                    'created_at': row['created_at']
                })
    return flashcards

def get_user_collections(user_email):
    """
    Get all unique collection names for a specific user.
    Collections are groups of flashcards (e.g., "Algebra", "Geometry").
    Args:
        user_email: Email of the user whose collections to retrieve
    Returns:
        Sorted list of unique collection names
    """
    flashcards = get_user_flashcards(user_email)
    collections = set()  # Use set to automatically handle uniqueness
    for card in flashcards:
        if card['collection']:  # Only add non-empty collections
            collections.add(card['collection'])
    return sorted(list(collections))  # Return sorted list for consistent display

def save_flashcard(user_email, name, question, answer, collection='', image_question='', image_answer=''):
    """
    Save a new flashcard for a user.
    Args:
        user_email: Email of the user creating the flashcard
        name: Optional name/title for the flashcard (empty string if not provided)
        question: The question text
        answer: The answer text
        collection: Optional collection name (empty string for uncategorized)
        image_question: Optional base64-encoded image for question (empty string if not provided)
        image_answer: Optional base64-encoded image for answer (empty string if not provided)
    Returns:
        The ID of the newly created flashcard
    """
    # Ensure CSV file exists with proper headers
    init_flashcards_csv()
    # Get next available ID
    card_id = get_next_flashcard_id()
    # Generate timestamp
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Append new flashcard to CSV file
    with open(FLASHCARDS_CSV, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([card_id, user_email, name, question, answer, image_question, image_answer, collection, created_at])
    return card_id

def update_flashcard(card_id, user_email, name, question, answer, collection='', image_question='', image_answer=''):
    """
    Update an existing flashcard.
    Reads all flashcards, updates the matching one, and writes all back.
    Args:
        card_id: ID of the flashcard to update
        user_email: Email of the user (for security - ensures user owns the card)
        name: Updated name/title for the flashcard
        question: Updated question text
        answer: Updated answer text
        collection: Updated collection name
        image_question: Updated base64-encoded image for question (empty string to remove image)
        image_answer: Updated base64-encoded image for answer (empty string to remove image)
    Returns:
        True if update was successful, False otherwise
    """
    if not os.path.exists(FLASHCARDS_CSV):
        return False
    
    # Read all flashcards
    flashcards = []
    with open(FLASHCARDS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Find the card to update (must match both ID and user email for security)
            if row['id'] == str(card_id) and row['user_email'].lower() == user_email.lower():
                # Update this card's fields
                row['name'] = name
                row['question'] = question
                row['answer'] = answer
                row['collection'] = collection
                # Update images (only if provided, otherwise keep existing)
                if image_question is not None:
                    row['image_question'] = image_question
                if image_answer is not None:
                    row['image_answer'] = image_answer
            flashcards.append(row)
    
    # Write back all flashcards (including the updated one)
    with open(FLASHCARDS_CSV, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'user_email', 'name', 'question', 'answer', 'image_question', 'image_answer', 'collection', 'created_at'])
        for card in flashcards:
            writer.writerow([card['id'], card['user_email'], card.get('name', ''), card['question'], card['answer'], card.get('image_question', ''), card.get('image_answer', ''), card.get('collection', ''), card['created_at']])
    
    return True

def delete_flashcard(card_id, user_email):
    """
    Delete a flashcard by reading all flashcards except the one to delete.
    Args:
        card_id: ID of the flashcard to delete
        user_email: Email of the user (for security - ensures user owns the card)
    Returns:
        True if deletion was successful, False otherwise
    """
    if not os.path.exists(FLASHCARDS_CSV):
        return False
    
    # Read all flashcards except the one to delete
    flashcards = []
    with open(FLASHCARDS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Keep all cards except the one matching both ID and user email
            if not (row['id'] == str(card_id) and row['user_email'].lower() == user_email.lower()):
                flashcards.append(row)
    
    # Write back all flashcards except the deleted one
    with open(FLASHCARDS_CSV, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'user_email', 'name', 'question', 'answer', 'image_question', 'image_answer', 'collection', 'created_at'])
        for card in flashcards:
            writer.writerow([card['id'], card['user_email'], card.get('name', ''), card['question'], card['answer'], card.get('image_question', ''), card.get('image_answer', ''), card.get('collection', ''), card['created_at']])
    
    return True

def get_flashcard_by_id(card_id, user_email):
    """
    Get a specific flashcard by ID, ensuring it belongs to the specified user.
    Args:
        card_id: ID of the flashcard to retrieve
        user_email: Email of the user (for security)
    Returns:
        Dictionary with flashcard data if found, None otherwise
    """
    if not os.path.exists(FLASHCARDS_CSV):
        return None
    
    with open(FLASHCARDS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Must match both ID and user email for security
            if row['id'] == str(card_id) and row['user_email'].lower() == user_email.lower():
                return {
                    'id': row['id'],
                    'name': row.get('name', ''),
                    'question': row['question'],
                    'answer': row['answer'],
                    'image_question': row.get('image_question', ''),
                    'image_answer': row.get('image_answer', ''),
                    'collection': row.get('collection', ''),
                    'created_at': row['created_at']
                }
    return None

# ============================================================================
# Flask Route Handlers
# ============================================================================

@app.route("/")
def home():
    """
    Home page route - displays welcome message and navigation.
    Accessible to all users (logged in or not).
    """
    return render_template("index.html")


@app.route("/practice")
def practice():
    """
    Practice page route - displays user's flashcards organized by collections.
    Requires user to be logged in.
    """
    # Check if user is logged in
    if 'user' not in session:
        flash('Please log in to access the practice page.', 'error')
        return redirect(url_for('login'))
    
    # Migrate flashcards if needed (for backward compatibility)
    migrate_flashcards_csv()
    
    # Get user's flashcards and collections to display
    user_flashcards = get_user_flashcards(session['user']['email'])
    user_collections = get_user_collections(session['user']['email'])
    return render_template("practice.html", flashcards=user_flashcards, collections=user_collections)


@app.route("/add_flashcard", methods=['POST'])
def add_flashcard():
    """
    Handle adding a new flashcard via POST request.
    Validates input and saves the flashcard to CSV.
    """
    if 'user' not in session:
        flash('Please log in to add flashcards.', 'error')
        return redirect(url_for('login'))
    
    # Get form data
    name = request.form.get('name', '').strip()  # Optional name field
    question = request.form.get('question')
    answer = request.form.get('answer')
    collection = request.form.get('collection', '').strip()  # Strip whitespace from collection name
    # Get image data (base64 encoded from hidden inputs)
    image_question = request.form.get('image_question', '').strip()
    image_answer = request.form.get('image_answer', '').strip()
    
    # Validate that both question and answer are provided
    if not question or not answer:
        flash('Both question and answer are required!', 'error')
        return redirect(url_for('practice'))
    
    try:
        # Save the flashcard
        save_flashcard(session['user']['email'], name, question, answer, collection, image_question, image_answer)
        flash('Flashcard added successfully!', 'success')
    except Exception as e:
        flash('An error occurred while saving the flashcard.', 'error')
    
    return redirect(url_for('practice'))


@app.route("/edit_flashcard/<int:card_id>", methods=['GET', 'POST'])
def edit_flashcard(card_id):
    """
    Handle editing a flashcard - supports both GET (show form) and POST (save changes).
    Args:
        card_id: ID of the flashcard to edit
    """
    if 'user' not in session:
        flash('Please log in to edit flashcards.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Handle form submission
        name = request.form.get('name', '').strip()  # Optional name field
        question = request.form.get('question')
        answer = request.form.get('answer')
        collection = request.form.get('collection', '').strip()
        # Get image data (base64 encoded from hidden inputs)
        image_question = request.form.get('image_question', '').strip()
        image_answer = request.form.get('image_answer', '').strip()
        
        # Validate input
        if not question or not answer:
            flash('Both question and answer are required!', 'error')
            return redirect(url_for('practice'))
        
        try:
            # Update the flashcard
            if update_flashcard(card_id, session['user']['email'], name, question, answer, collection, image_question, image_answer):
                flash('Flashcard updated successfully!', 'success')
            else:
                flash('Flashcard not found or you do not have permission to edit it.', 'error')
        except Exception as e:
            flash('An error occurred while updating the flashcard.', 'error')
        
        return redirect(url_for('practice'))
    
    # GET request - show edit form with current flashcard data
    flashcard = get_flashcard_by_id(card_id, session['user']['email'])
    if not flashcard:
        flash('Flashcard not found or you do not have permission to edit it.', 'error')
        return redirect(url_for('practice'))
    
    # Get user's collections for the collection dropdown
    user_collections = get_user_collections(session['user']['email'])
    return render_template("edit_flashcard.html", flashcard=flashcard, collections=user_collections)


@app.route("/delete_flashcard/<int:card_id>", methods=['POST'])
def delete_flashcard_route(card_id):
    """
    Handle deleting a flashcard via POST request.
    Args:
        card_id: ID of the flashcard to delete
    """
    if 'user' not in session:
        flash('Please log in to delete flashcards.', 'error')
        return redirect(url_for('login'))
    
    try:
        if delete_flashcard(card_id, session['user']['email']):
            flash('Flashcard deleted successfully!', 'success')
        else:
            flash('Flashcard not found or you do not have permission to delete it.', 'error')
    except Exception as e:
        flash('An error occurred while deleting the flashcard.', 'error')
    
    return redirect(url_for('practice'))


@app.route("/login", methods=['GET', 'POST'])
def login():
    """
    Handle user login - supports both GET (show form) and POST (process login).
    On successful login, stores user data in session and redirects to home.
    """
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate input
        if not email or not password:
            flash('Please enter both email and password!', 'error')
            return render_template("login.html")
        
        # Verify credentials
        user = verify_user(email, password)
        if user:
            # Store user info in session (persists across requests)
            session['user'] = user
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password!', 'error')
            return render_template("login.html")
    
    # GET request - show login form
    return render_template("login.html")


@app.route("/register", methods=['POST'])
def register():
    """
    Handle user registration via POST request.
    Validates input, checks for duplicate emails, and creates new user account.
    """
    # Get form data
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # Validation - check all fields are provided
    if not all([name, email, password, confirm_password]):
        flash('All fields are required!', 'error')
        return render_template("login.html")
    
    # Check passwords match
    if password != confirm_password:
        flash('Passwords do not match!', 'error')
        return render_template("login.html")
    
    # Check password length
    if len(password) < 6:
        flash('Password must be at least 6 characters long!', 'error')
        return render_template("login.html")
    
    # Check if email already exists
    if email_exists(email):
        flash('Email already registered! Please use a different email or try logging in.', 'error')
        return render_template("login.html")
    
    try:
        # Initialize CSV file if it doesn't exist
        init_users_csv()
        
        # Save user data to CSV
        save_user_to_csv(name, email, password)
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    except Exception as e:
        flash('An error occurred during registration. Please try again.', 'error')
        return render_template("login.html")


@app.route("/logout")
def logout():
    """
    Handle user logout - removes user data from session.
    """
    session.pop('user', None)  # Remove user from session
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('home'))


@app.route("/delete_collection/<collection_name>", methods=['POST'])
def delete_collection_route(collection_name):
    """
    Handle deleting an entire collection (all flashcards in that collection).
    Args:
        collection_name: Name of the collection to delete
    """
    if 'user' not in session:
        flash('Please log in to delete collections.', 'error')
        return redirect(url_for('login'))
    
    try:
        if delete_collection(collection_name, session['user']['email']):
            flash(f'Collection "{collection_name}" deleted successfully!', 'success')
        else:
            flash('Collection not found or you do not have permission to delete it.', 'error')
    except Exception as e:
        flash('An error occurred while deleting the collection.', 'error')
    
    return redirect(url_for('practice'))


def delete_collection(collection_name, user_email):
    """
    Delete all flashcards in a specific collection for a user.
    Reads all flashcards, filters out those in the collection, and writes back.
    Args:
        collection_name: Name of the collection to delete
        user_email: Email of the user (for security)
    Returns:
        True if deletion was successful, False otherwise
    """
    if not os.path.exists(FLASHCARDS_CSV):
        return False
    
    # Read all flashcards except those in the collection to delete
    flashcards = []
    with open(FLASHCARDS_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Keep all cards except those matching the collection name and user email
            if not (row['collection'] == collection_name and row['user_email'].lower() == user_email.lower()):
                flashcards.append(row)
    
    # Write back all flashcards except the deleted ones
    with open(FLASHCARDS_CSV, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'user_email', 'name', 'question', 'answer', 'image_question', 'image_answer', 'collection', 'created_at'])
        for card in flashcards:
            writer.writerow([card['id'], card['user_email'], card.get('name', ''), card['question'], card['answer'], card.get('image_question', ''), card.get('image_answer', ''), card.get('collection', ''), card['created_at']])
    
    return True


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    # Run the Flask development server
    # debug=True enables auto-reload on code changes and detailed error pages
    app.run(debug=True)
