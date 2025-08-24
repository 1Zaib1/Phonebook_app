from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import json
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Data structures
contacts = {}
call_log = defaultdict(list)  # Store detailed call logs with timestamps
relationships = defaultdict(set)  # Graph-like adjacency list for relationships

# Load data from JSON files
def load_data():
    global contacts, call_log
    try:
        with open('contacts.json', 'r') as file:
            contacts = json.load(file)
        with open('call_log.json', 'r') as file:
            call_log = defaultdict(list, json.load(file))
    except FileNotFoundError:
        contacts, call_log = {}, defaultdict(list)

# Save data to JSON files
def save_data():
    with open('contacts.json', 'w') as file:
        json.dump(contacts, file)
    with open('call_log.json', 'w') as file:
        json.dump(call_log, file)

load_data()

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for char in word.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True

    def search(self, prefix):
        node = self.root
        for char in prefix.lower():
            if char not in node.children:
                return []
            node = node.children[char]
        return self._collect_all_words(node, prefix)

    def _collect_all_words(self, node, prefix):
        words = []
        if node.is_end_of_word:
            words.append(prefix)
        for char, child_node in node.children.items():
            words.extend(self._collect_all_words(child_node, prefix + char))
        return words

trie = Trie()

for contact_name in contacts:
    trie.insert(contact_name)

def validate_phone(phone):
    return phone.isdigit() and len(phone) >= 10

def validate_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

@app.route('/contacts', methods=['GET'])
def get_contacts():
    return jsonify(contacts)

@app.route('/contacts', methods=['POST'])
def add_contact():
    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email', '')
    address = data.get('address', '')
    group = data.get('group', '')
    favorite = data.get('favorite', False)

    if not name or not phone:
        return jsonify({"error": "Name and phone number are required"}), 400

    if not validate_phone(phone):
        return jsonify({"error": "Invalid phone number format"}), 400

    if email and not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    contacts[name.lower()] = {
        'phone': phone,
        'email': email,
        'address': address,
        'group': group,
        'favorite': favorite
    }
    trie.insert(name)
    save_data()
    return jsonify({"message": "Contact added successfully"}), 201

@app.route('/contacts/<name>', methods=['PUT'])
def update_contact(name):
    key = name.lower()
    if key not in contacts:
        return jsonify({"error": "Contact not found"}), 404

    data = request.get_json()
    phone = data.get('phone')
    email = data.get('email')
    address = data.get('address')
    group = data.get('group')
    favorite = data.get('favorite')

    if phone and not validate_phone(phone):
        return jsonify({"error": "Invalid phone number format"}), 400

    if email and not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    contact = contacts[key]
    if phone:
        contact['phone'] = phone
    if email:
        contact['email'] = email
    if address:
        contact['address'] = address
    if group:
        contact['group'] = group
    if favorite is not None:
        contact['favorite'] = favorite

    save_data()
    return jsonify({"message": "Contact updated successfully"}), 200

@app.route('/contacts/<name>', methods=['DELETE'])
def delete_contact(name):
    key = name.lower()
    if key in contacts:
        del contacts[key]
        save_data()
        return jsonify({"message": "Contact deleted successfully"}), 200
    else:
        return jsonify({"error": "Contact not found"}), 404

@app.route('/contacts/search', methods=['GET'])
def search_contact():
    query = request.args.get('query', '').lower()
    results = trie.search(query)
    result_contacts = {name: contacts[name.lower()] for name in results if name.lower() in contacts}
    return jsonify(result_contacts)

@app.route('/contacts/advanced-search', methods=['GET'])
def advanced_search():
    phone = request.args.get('phone')
    email = request.args.get('email')
    address = request.args.get('address')
    results = {
        name: details for name, details in contacts.items()
        if (not phone or phone in details['phone']) and
           (not email or email.lower() in details['email'].lower()) and
           (not address or address.lower() in details['address'].lower())
    }
    return jsonify(results)

@app.route('/contacts/favorites', methods=['GET'])
def get_favorites():
    favorites = {name: details for name, details in contacts.items() if details.get('favorite')}
    return jsonify(favorites)

@app.route('/contacts/relationship/<name1>/<name2>', methods=['POST'])
def add_relationship(name1, name2):
    key1, key2 = name1.lower(), name2.lower()
    if key1 not in contacts or key2 not in contacts:
        return jsonify({"error": "One or both contacts not found"}), 404
    relationships[key1].add(key2)
    relationships[key2].add(key1)
    save_data()
    return jsonify({"message": f"Relationship added between {name1} and {name2}"}), 200

@app.route('/contacts/graph', methods=['GET'])
def get_graph():
    return jsonify({name: list(neighbors) for name, neighbors in relationships.items()})

@app.route('/call/<name>', methods=['POST'])
def log_call(name):
    key = name.lower()
    if key not in contacts:
        return jsonify({"error": "Contact not found"}), 404
    call_log[key].append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    save_data()
    return jsonify({"message": f"Call logged for {name}"}), 200

@app.route('/call-log', methods=['GET'])
def get_call_log():
    return jsonify(call_log)

if __name__ == '__main__':
    app.run(debug=True)
