import json
import re
from typing import List, Dict


def generate_slide_content(text_content: str, guidance: str = "", llm_provider: str = "openai", api_key: str = "") -> List[Dict]:
    """
    Calls an LLM API to generate structured slide content from input text.
    Returns a list of dictionaries with slide data.
    """
    if not api_key:
        raise ValueError("API key is required")
    
    # Create the prompt
    base_prompt = f"""
Convert the following text into a structured PowerPoint presentation. 

Text to convert:
{text_content}

Additional guidance: {guidance if guidance else "Standard presentation format"}

Requirements:
1. Analyze the content and determine the optimal number of slides (typically 5-12 slides)
2. Create a logical flow with clear sections
3. Extract key points and organize them hierarchically
4. Ensure each slide has a clear, descriptive title
5. Include 2-6 bullet points per slide maximum
6. Make content concise and presentation-friendly

Return the response as a JSON array with this exact format:
[
  {{
    "title": "Introduction",
    "points": ["Key point 1", "Key point 2", "Key point 3"]
  }},
  {{
    "title": "Main Topic",
    "points": ["Supporting detail 1", "Supporting detail 2"]
  }}
]

Important: Return ONLY the JSON array, no additional text or formatting.
"""

    try:
        if llm_provider.lower() == "openai":
            return _call_openai(base_prompt, api_key)
        elif llm_provider.lower() == "anthropic":
            return _call_anthropic(base_prompt, api_key)
        elif llm_provider.lower() == "gemini":
            return _call_gemini(base_prompt, api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
    
    except Exception as e:
        print(f"Error calling LLM API: {str(e)}")
        # Fallback: create slides from text analysis
        return _fallback_text_analysis(text_content, guidance)

def _call_openai(prompt: str, api_key: str) -> List[Dict]:
    """Call OpenAI API"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a presentation expert who converts text into structured slide content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        return _parse_llm_response(content)
    
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        raise

def _call_anthropic(prompt: str, api_key: str) -> List[Dict]:
    """Call Anthropic API"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text.strip()
        return _parse_llm_response(content)
    
    except Exception as e:
        print(f"Anthropic API error: {str(e)}")
        raise

def _call_gemini(prompt: str, api_key: str) -> List[Dict]:
    """Call Google Gemini API"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash-latest") 
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        return _parse_llm_response(content)
    
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        raise

def _parse_llm_response(content: str) -> List[Dict]:
    """Parse LLM response and extract JSON"""
    try:
        # Try to find JSON in the response
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            # Try parsing the entire content as JSON
            return json.loads(content)
    
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {str(e)}")
        print(f"Raw content: {content}")
        # Fallback to manual parsing
        return _manual_parse_response(content)

def _manual_parse_response(content: str) -> List[Dict]:
    """Manually parse LLM response if JSON parsing fails"""
    slides = []
    lines = content.strip().split('\n')
    current_slide = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this looks like a title (various formats)
        if (line.startswith('#') or 
            line.startswith('**') and line.endswith('**') or
            line.endswith(':') or
            (len(line.split()) <= 6 and not line.startswith('-') and not line.startswith('*'))):
            
            # Save previous slide if exists
            if current_slide:
                slides.append(current_slide)
            
            # Start new slide
            title = line.strip('# *:').strip()
            current_slide = {"title": title, "points": []}
        
        elif line.startswith(('-', '*', '•')) or line[0].isdigit() and line[1] in '.):':
            # This is a bullet point
            if current_slide:
                point = re.sub(r'^[-*•]\s*', '', line)
                point = re.sub(r'^\d+[.):]\s*', '', point)
                current_slide["points"].append(point.strip())
    
    # Add the last slide
    if current_slide:
        slides.append(current_slide)
    
    # Ensure we have at least one slide
    if not slides:
        slides.append({
            "title": "Content Overview", 
            "points": [content[:200] + "..." if len(content) > 200 else content]
        })
    
    return slides

def _fallback_text_analysis(text_content: str, guidance: str) -> List[Dict]:
    """Fallback method to create slides without LLM"""
    print("Using fallback text analysis...")
    
    # Simple text analysis approach
    paragraphs = [p.strip() for p in text_content.split('\n\n') if p.strip()]
    
    if len(paragraphs) <= 1:
        # Split by sentences if no clear paragraphs
        sentences = [s.strip() for s in text_content.split('.') if s.strip()]
        paragraphs = []
        current_para = ""
        for i, sentence in enumerate(sentences):
            current_para += sentence + ". "
            if (i + 1) % 3 == 0 or i == len(sentences) - 1:
                paragraphs.append(current_para.strip())
                current_para = ""
    
    slides = []
    
    # Create title slide
    title = "Presentation Overview"
    if guidance:
        title = f"{guidance.title()}"
    
    slides.append({
        "title": title,
        "points": [f"Based on provided content", f"Generated automatically"]
    })
    
    # Create content slides
    for i, para in enumerate(paragraphs[:10]):  # Limit to 10 content slides
        slide_title = f"Topic {i+1}"
        
        # Try to extract a title from the first sentence
        first_sentence = para.split('.')[0].strip()
        if len(first_sentence.split()) <= 8:
            slide_title = first_sentence
        
        # Split paragraph into points
        sentences = [s.strip() + '.' for s in para.split('.') if s.strip()]
        points = sentences[:5]  # Max 5 points per slide
        
        slides.append({
            "title": slide_title,
            "points": points
        })
    
    return slides