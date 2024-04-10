import re
import os
import whisper
import asyncio
import aiohttp
import nltk
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from io import BytesIO
import librosa
import numpy as np
from PyPDF2 import PdfReader
from flask import session
import openai, requests
from pdfminer.high_level import extract_text
openai.api_key = os.getenv('OPENAI_API_KEY')

def extract_text_from_pdf(file_storage):
    """
    Extracts text from a PDF file. The input can be a file path, a file-like object,
    or binary content.

    Args:
        file_storage (str, file-like object, bytes): The source of the PDF.

    Returns:
        str: Extracted text if successful, None otherwise.
    """
    try:
        if isinstance(file_storage, str) and os.path.isfile(file_storage):
            # Handle file path
            with open(file_storage, 'rb') as file:
                return extract_text_from_pdf_stream(file)
        elif hasattr(file_storage, 'read'):
            # Handle file-like object
            return extract_text_from_pdf_stream(file_storage)
        elif isinstance(file_storage, bytes):
            # Handle binary data
            with BytesIO(file_storage) as file_stream:
                return extract_text_from_pdf_stream(file_stream)
        else:
            raise ValueError("Unsupported file storage type")
    except Exception as e:
        print(f"Error processing file: {e}")
        return None

def extract_text_from_pdf_stream(stream):
    """
    Extracts text from a PDF file stream.

    Args:
        stream (file-like object): The PDF file stream.

    Returns:
        str: Extracted text.
    """
    pdf_reader = PdfReader(stream)
    text = ''.join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
    return text

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).lower()
    return text

def segment_text(text, max_length=5000):
    segments = []
    current_segment = ''
    for paragraph in text.split('\n'):
        if len(current_segment) + len(paragraph) > max_length:
            segments.append(current_segment)
            current_segment = paragraph
        else:
            current_segment += ' ' + paragraph
    if current_segment:
        segments.append(current_segment)
    return segments

def is_heading(line):
    """
    Detect if a line is likely a heading. 
    Simple heuristic: line is a heading if it's a title case or has numbering.
    """
    return line.istitle() or re.match(r'^\s*\d+(\.\d+)*\s', line)

def segment_text_by_headings(text, max_tokens_per_segment):
    segments = []
    current_segment = []
    current_token_count = 0

    for line in text.split('\n'):
        line_token_count = len(line.split())

        # Check for new heading and segment length
        if is_heading(line) and current_token_count > max_tokens_per_segment / 2:
            segments.append(' '.join(current_segment))
            current_segment = [line]
            current_token_count = line_token_count
        else:
            if current_token_count + line_token_count <= max_tokens_per_segment:
                current_segment.append(line)
                current_token_count += line_token_count
            else:
                # Further segment the current segment at a natural breakpoint
                breakpoint = line[:max_tokens_per_segment - current_token_count].rfind('. ')
                if breakpoint == -1:
                    breakpoint = max_tokens_per_segment - current_token_count

                # Add the first part to the current segment and start a new one
                current_segment.append(line[:breakpoint])
                segments.append(' '.join(current_segment))

                current_segment = [line[breakpoint:]]
                current_token_count = len(current_segment[0].split())

    # Add the final segment
    if current_segment:
        segments.append(' '.join(current_segment))

    return segments



def generate_questions(context, question_type="multiple_choice", num_questions=1, model="gpt-3.5-turbo-instruct"):
    if question_type == "true_false":
        prompt = prompt = (f"Generate {num_questions} True/False questions based exclusively on the following text, Start each question with 'True or False:' and ensure they are directly related to the text, Do not include answers. Here is the text:\n\n {context},IMPORTANT: Do not include the context or any preamble before the question.")
    elif question_type == "short_answer":
        prompt = prompt = (f"Create {num_questions} short answer questions that are directly related to the following text, Start each question with 'Q:' to clearly indicate a question, Focus on key points in the text. Text for questions:\n\n{context}, IMPORTANT: Do not include the context or any preamble before the question.")
    # Add more conditions for other types of questions
    else:  # Default to multiple choice
        prompt = (f"Formulate {num_questions} multiple choice questions based on the following text, Each question should be followed by four options labeled A, B, C, and D, Only one option should be correct. Text to use:\n\n{context},IMPORTANT: Do not include the context or any preamble before the question.")
    try:
        response = openai.Completion.create(engine=model, prompt=prompt, max_tokens=100, n=num_questions)
        questions = [choice.text.strip() for choice in response.choices]
        return questions
    except Exception as e:
        print(f"Error in GPT API request: {e}")
        return []


def evaluate_answer(context, question, user_answer, model="gpt-3.5-turbo-instruct"):
    prompt = f"Based on the text: '{context}', evaluate the following answer.\nQuestion: {question}\nAnswer: {user_answer}\nIs this answer correct? Explain why or why not. Always talk in english language."
    try:
        response = openai.Completion.create(engine=model, prompt=prompt, max_tokens=100)
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error in GPT API request: {e}")
        return None

    
def generate_condensed_script(text, model="gpt-3.5-turbo-instruct"):
    """
    Transforms a given text into a concise, well-structured script using OpenAI's GPT model.

    Parameters:
    text (str): The input text to be condensed.
    model (str): The model to use for text generation. Default is 'gpt-3.5-turbo-instruct'.

    Returns:
    str: The generated condensed script or an error message.
    """

    # Validate input parameters
    if not isinstance(text, str) or not text.strip():
        return "Invalid input text. Please provide a non-empty string."
    if not isinstance(model, str) or not model.strip():
        return "Invalid model name. Please provide a valid model string."

    # Estimation of the number of tokens in the prompt
    prompt_length = len(text.split())

    # Maximum tokens allowed for the completion, considering some buffer for safety
    max_completion_length = min(max(3000 - prompt_length - 50, 0), 500)  # 50 tokens buffer, limit to 500

    # Construct a more directive prompt
    prompt = (
        "Please condense the following text into a concise and coherent script. "
        "Avoid unnecessary numbering and focus on clear explanations. "
        "The script should highlight key ideas, simplify complex concepts, and be organized with headings and bullet points for easy understanding:\n\n"
        f"Text:\n\n{text}"
    )

    try:
        response = openai.Completion.create(
            engine=model, 
            prompt=prompt, 
            max_tokens=max_completion_length
        )
        generated_text = response.choices[0].text.strip()

        return generated_text if generated_text else "The response was empty. Please adjust the input text or try again."
    except openai.error.InvalidRequestError as e:
        return f"Error: Token limit exceeded. Reduce the length of input text. Details: {e}"
    except Exception as e:
        print(f"Error in GPT API request: {e}")
        return "An unexpected error occurred. Please try again."


def clean_up_script(script):
    # Remove repeated headings
    seen_headings = set()
    seen_sentences = set()
    lines = script.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped_line = line.strip()
        # Check for repeated headings
        if stripped_line.endswith(':'):
            if stripped_line in seen_headings:
                continue
            seen_headings.add(stripped_line)
        # Check for repeated sentences
        elif stripped_line and stripped_line not in seen_sentences:
            seen_sentences.add(stripped_line)
        else:
            continue  # Skip adding the line if it's a repeated sentence

        cleaned_lines.append(line)

    # Replace different bullet points with a standard one
    cleaned_script = '\n'.join(cleaned_lines)
    cleaned_script = cleaned_script.replace('•', '-').replace('*', '-')

    return cleaned_script

def analyze_essay(essay_text):
    # OpenAI API key setup (make sure your key is correctly configured)

    # Constructing a prompt for the AI model
    prompt = f"Perform a comprehensive analysis of the essay focusing on grammar, structure, and content relevance. After your analysis, provide detailed and constructive feedback on areas that require improvement. Your evaluation should be thorough and helpful for the writer's improvement:\n\n{essay_text} Please ensure that your analysis covers all aspects mentioned, and offer suggestions for enhancement wherever necessary."

    try:
        # Sending the prompt to the AI model
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",  # or the latest available model
            prompt=prompt,
            max_tokens=500  # You can adjust this based on how lengthy you expect the feedback to be
        )
        feedback = response.choices[0].text.strip()
    except Exception as e:
        print(f"Error in AI model response: {e}")
        feedback = "An error occurred while processing the essay."

    return feedback

def analyze_pdf_essay(pdf_text, max_tokens_per_segment=1000):
    """
    Analyzes a large essay text from a PDF, segmented by headings.

    Parameters:
    pdf_text (str): The essay text extracted from a PDF.
    max_tokens_per_segment (int): Maximum number of tokens per segment.

    Returns:
    list: List of feedback for each segmented part of the essay.
    """
    feedback_list = []
    segments = segment_text_by_headings(pdf_text, max_tokens_per_segment)

    for segment in segments:
        feedback = analyze_essay(segment)
        feedback_list.append(feedback)

    return feedback_list

def main():
    pdf_path = 'VJ_10-aritmetički_sklopovi (5).pdf'
    pdf_text = extract_text_from_pdf(pdf_path)

    if pdf_text:
        context = clean_text(pdf_text)
        context_segmented = " ".join(segment_text(context))

        while True:
            generated_questions = generate_questions(context_segmented, num_questions=1)
            if not generated_questions:
                print("Failed to generate questions. Exiting.")
                break

            print("Generated Question:", generated_questions)
            user_answer = input("Your answer (type 'exit' to stop): ")

            if user_answer.lower() == 'exit':
                break

            evaluated_answer = evaluate_answer(context_segmented, generated_questions, user_answer)
            if evaluated_answer:
                print("Evaluation:", evaluated_answer)
            else:
                print("Failed to evaluate the answer.")
            print("\n")

    else:
        print("Failed to extract text.")

def initialize_model():
    # Load and return the Whisper model
    model = whisper.load_model("base")
    return model

def transcribe_audio(model, file_stream):
    # Load and preprocess audio
    audio_data, _ = librosa.load(file_stream, sr=16000)  # Resample to 16kHz
    audio_np = np.array(audio_data)

    # Transcribe
    result = model.transcribe(audio_np)
    return result["text"]

def generate_summary(text, model="gpt-3.5-turbo-instruct"):
    """
    Generates a summary of the given text using OpenAI's GPT model.

    Parameters:
    text (str): The input text to be summarized.
    model (str): The model to use for text generation. Default is 'gpt-3.5-turbo-instruct'.

    Returns:
    str: The generated summary or an error message.
    """

    if not text:
        return "No text provided."

    prompt = f"Summarize the following text:\n\n{text}"

    try:
        response = openai.Completion.create(
            engine=model, 
            prompt=prompt, 
            max_tokens=150  # Adjust as needed
        )
        summary = response.choices[0].text.strip()

        return summary if summary else "The response was empty. Please try again."
    except Exception as e:
        print(f"Error in GPT API request: {e}")
        return "An unexpected error occurred. Please try again."

def summarize_pdf(file_storage):
    """
    Extracts text from a PDF file and generates its summary.

    Parameters:
    file_storage: The PDF file storage object (file path or file-like object).

    Returns:
    str: The generated summary of the PDF content.
    """
    pdf_text = extract_text_from_pdf(file_storage)
    if pdf_text:
        return generate_summary(pdf_text)
    else:
        return "Failed to extract text from PDF."

if __name__ == "__main__":
    main()