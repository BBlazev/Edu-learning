import openai
import os, re
from flask import Flask, request, render_template, jsonify
# ... other imports ...

# Your existing Flask setup
app = Flask(__name__)
# ... other configurations ...

# Initialize OpenAI
openai.api_key = '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'

# Mind map generation logic (simplified for this example)
def generate_mind_map(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )

    # Extract the text response
    text_response = response.choices[0].text

    # Process the response to create a mind map
    # Assuming the GPT model gives responses like "add('Node1', 'Node2')"
    pattern = r"add\('([^']*)',\s*'([^']*)'\)"
    edges = re.findall(pattern, text_response)

    # Creating a simple representation of the mind map
    # This could be a list of edges, or a more complex structure like a graph object
    mind_map_data = {
        "edges": edges
    }

    return mind_map_data

if __name__ == '__main__':
    app.run(debug=True)