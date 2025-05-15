from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime
import os
from transformers import pipeline
import numpy as np

app = Flask(__name__)

# Tool 1: Math operations
@app.route('/tools/math', methods=['POST'])
def math_tool():
    data = request.json
    operation = data.get('operation')
    try:
        a = float(data.get('a', 0))
        b = float(data.get('b', 0))
    except ValueError:
        return jsonify({"status": "error", "message": "Operands must be numbers"}), 400

    result = None
    if operation == 'add':
        result = a + b
    elif operation == 'subtract':
        result = a - b
    elif operation == 'multiply':
        result = a * b
    elif operation == 'divide':
        if b == 0:
            return jsonify({"status": "error", "message": "Cannot divide by zero"}), 400
        result = a / b
    else:
        return jsonify({"status": "error", "message": f"Unknown operation: {operation}"}), 400

    return jsonify({"status": "success", "result": result})


# Tool 2: Weather information (simulated)
@app.route('/tools/weather', methods=['POST'])
def weather_tool():
    data = request.json
    location = data.get('location', '').lower()

    # Simulate weather data
    weather_data = {
        'new york': {'temperature': 22, 'condition': 'Sunny'},
        'london': {'temperature': 15, 'condition': 'Rainy'},
        'tokyo': {'temperature': 28, 'condition': 'Clear'},
        'sydney': {'temperature': 20, 'condition': 'Partly Cloudy'}
    }

    if location in weather_data:
        return jsonify({
            "status": "success",
            "result": weather_data[location]
        })
    else:
        return jsonify({
            "status": "success",
            "result": {'temperature': 18, 'condition': 'Unknown location'}
        })

# Tool 3: Date and time
@app.route('/tools/datetime', methods=['POST'])
def datetime_tool():
    data = request.json
    format_str = data.get('format', '%Y-%m-%d %H:%M:%S')

    try:
        current_time = datetime.now().strftime(format_str)
        return jsonify({"status": "success", "result": current_time})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# Load sentiment analysis pipeline (as a proxy for creativity scoring)
# In a real implementation, you might use a more sophisticated model
sentiment_analyzer = pipeline("sentiment-analysis")

# Tool 4: Creativity Evaluator
@app.route('/tools/creativity_score', methods=['POST'])
def creativity_score_tool():
    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({"status": "error", "message": "No text provided"}), 400

    try:
        # This is a simplified creativity scoring algorithm
        # Real implementations would use more sophisticated approaches

        # 1. Length factor (longer texts might have more creative elements)
        length_score = min(len(text) / 500, 1.0) * 20  # Max 20 points

        # 2. Sentiment diversity (proxy for emotional range)
        chunks = [text[i:i+100] for i in range(0, len(text), 100)]
        if not chunks:
            chunks = [text]

        sentiments = [sentiment_analyzer(chunk)[0] for chunk in chunks if chunk.strip()]
        sentiment_scores = [s['score'] for s in sentiments]
        sentiment_diversity = np.std(sentiment_scores) if len(sentiment_scores) > 1 else 0.5
        emotion_score = sentiment_diversity * 30  # Max 30 points

        # 3. Vocabulary richness (simple approximation)
        words = text.lower().split()
        unique_words = set(words)
        vocabulary_ratio = len(unique_words) / max(len(words), 1)
        vocabulary_score = vocabulary_ratio * 25  # Max 25 points

        # 4. Question factor (texts with questions might engage more)
        question_count = text.count('?')
        question_score = min(question_count * 5, 15)  # Max 15 points

        # 5. Uncommon punctuation (might indicate creative formatting)
        uncommon_punct = sum(1 for char in text if char in '!;:—"\'()[]{}')
        punct_score = min(uncommon_punct, 10)  # Max 10 points

        # Calculate total score
        total_score = length_score + emotion_score + vocabulary_score + question_score + punct_score
        normalized_score = min(round(total_score / 10), 10)  # 0-10 scale

        # Create detailed feedback
        feedback = {
            "overall_score": normalized_score,
            "breakdown": {
                "length": round(length_score / 20 * 10),
                "emotional_range": round(emotion_score / 30 * 10),
                "vocabulary_richness": round(vocabulary_score / 25 * 10),
                "engagement": round(question_score / 15 * 10),
                "stylistic_elements": round(punct_score / 10 * 10)
            },
            "strengths": [],
            "improvement_areas": []
        }

        # Generate feedback points
        if feedback["breakdown"]["vocabulary_richness"] >= 7:
            feedback["strengths"].append("Strong vocabulary diversity")
        elif feedback["breakdown"]["vocabulary_richness"] <= 4:
            feedback["improvement_areas"].append("Consider using more varied vocabulary")

        if feedback["breakdown"]["emotional_range"] >= 7:
            feedback["strengths"].append("Good emotional range and depth")
        elif feedback["breakdown"]["emotional_range"] <= 4:
            feedback["improvement_areas"].append("Try incorporating more emotional variety")

        if feedback["breakdown"]["length"] <= 3:
            feedback["improvement_areas"].append("The text might benefit from more development")

        if feedback["breakdown"]["engagement"] >= 7:
            feedback["strengths"].append("Engaging questioning style")

        return jsonify({
            "status": "success",
            "result": feedback
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# MCP Tool Manifest
@app.route('/manifest', methods=['GET'])
def manifest():
    return jsonify({
        "schema_version": "v1",
        "tools": [
            {
                "name": "math",
                "description": "Perform basic math operations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["add", "subtract", "multiply", "divide"],
                            "description": "The math operation to perform"
                        },
                        "a": {"type": "number", "description": "First operand"},
                        "b": {"type": "number", "description": "Second operand"}
                    },
                    "required": ["operation", "a", "b"]
                }
            },
            {
                "name": "weather",
                "description": "Get weather information for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The location to get weather for"
                        }
                    },
                    "required": ["location"]
                }
            },
            {
                "name": "datetime",
                "description": "Get current date and time",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "datetime format string (e.g., %Y-%m-%d %H:%M:%S)",
                            "default": "%Y-%m-%d %H:%M:%S"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "creativity_score",
                "description": "Evaluate the creativity level of a text on a scale of 0-10",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to evaluate for creativity"
                        }
                    },
                    "required": ["text"]
                }
            }
        ]
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)
