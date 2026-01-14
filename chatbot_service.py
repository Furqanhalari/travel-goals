from groq import Groq
import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GROQ_API_KEY')
client = None

if api_key:
    try:
        client = Groq(api_key=api_key)
        print("Groq API client initialized successfully")
    except Exception as e:
        print(f"Error initializing Groq client: {e}")
else:
    print("WARNING: GROQ_API_KEY not found in environment variables")


class TravelChatbot:
    """AI Travel Assistant using Groq API"""
    
    def __init__(self):
        """Initialize the chatbot with Groq client"""
        self.client = client
        self.model = "llama-3.3-70b-versatile"  
        self.initialized = self.client is not None
    
    def get_system_prompt(self, destinations, packages):
        """Generate context-aware system prompt with database info"""
        
        
        dest_names = ', '.join([d.get('name', 'Unknown') for d in destinations[:15]]) if destinations else 'Various destinations available'
        
        
        package_info = []
        for pkg in packages[:10]:
            name = pkg.get('name', 'Package')
            price = pkg.get('adult_price', pkg.get('price', 'N/A'))
            destination = pkg.get('destination_name', '')
            duration = pkg.get('duration_days', '')
            if destination:
                package_info.append(f"- {name} ({destination}, {duration} days, from ${price})")
            else:
                package_info.append(f"- {name} (from ${price})")
        
        packages_text = '\n'.join(package_info) if package_info else 'Multiple packages available'
        
        return f"""You are a friendly and helpful travel assistant for "Travel Goals" - a premium travel booking platform.

🌍 AVAILABLE DESTINATIONS:
{dest_names}

📦 FEATURED PACKAGES:
{packages_text}

👥 OUR VENDORS:
- PIA (Pakistan International Airlines)
- Fly Jinnah
- Air Blue

GUIDELINES:
1. Be friendly, enthusiastic, and concise (max 100 words)
2. Recommend specific destinations and packages from our list
3. Use travel emojis sparingly (✈️ 🌍 🏖️ 🗼 🎒)
4. When asked about booking, direct users to the Contact/Booking page
5. Highlight package features: duration, price, inclusions
6. For destinations not in our list, suggest similar available options
7. Cannot process payments or access personal booking history
8. If unsure, ask clarifying questions about preferences (budget, climate, activities)

Provide helpful, personalized travel advice and recommendations!"""

    def chat(self, user_message, destinations=None, packages=None, conversation_history=None):
        """
        Process user message and generate AI response
        
        Args:
            user_message: The user's input message
            destinations: List of available destinations from database
            packages: List of available packages from database
            conversation_history: Previous messages for context (optional)
        
        Returns:
            dict with 'success' boolean and 'message' string
        """
        if not self.initialized or not self.client:
            return {
                'success': False,
                'message': 'Chat service is currently unavailable. Please try again later.'
            }
        
        if not user_message or not user_message.strip():
            return {
                'success': False,
                'message': 'Please enter a message.'
            }
        
        destinations = destinations or []
        packages = packages or []
        
        try:
            
            system_prompt = self.get_system_prompt(destinations, packages)
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            
            if conversation_history:
                for msg in conversation_history[-10:]:
                    role = "user" if msg.get('role') == 'user' else "assistant"
                    messages.append({"role": role, "content": msg.get('content', '')})
            
            
            messages.append({"role": "user", "content": user_message})
            
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            
            
            if response and response.choices and len(response.choices) > 0:
                return {
                    'success': True,
                    'message': response.choices[0].message.content.strip()
                }
            else:
                return {
                    'success': False,
                    'message': 'I couldn\'t generate a response. Please try again.'
                }
                
        except Exception as e:
            print(f"Chatbot error: {e}")
            import traceback
            traceback.print_exc()
            
            
            user_lower = user_message.lower()
            
            if any(word in user_lower for word in ['book', 'booking', 'reserve']):
                return {
                    'success': True,
                    'message': '✈️ To make a booking, please visit our Contact/Booking page where you can submit your travel details. Our team will get back to you within 24 hours!'
                }
            elif any(word in user_lower for word in ['price', 'cost', 'how much', 'cheap', 'budget']):
                return {
                    'success': True,
                    'message': '💰 Our packages range from $900 to $2500+ depending on destination and duration. Visit the Packages page to see all options with detailed pricing!'
                }
            elif any(word in user_lower for word in ['destination', 'where', 'place', 'country']):
                return {
                    'success': True,
                    'message': '🌍 We offer amazing destinations including Paris, Tokyo, Dubai, Bali, Barcelona, London, and more! Check our Destinations page for the full list.'
                }
            else:
                return {
                    'success': False,
                    'message': 'Sorry, I encountered a temporary issue. Please try again in a moment.'
                }
    
    def get_quick_replies(self, context=None):
        """Generate contextual quick reply suggestions"""
        default_replies = [
            "🏖️ Beach destinations",
            "🏔️ Adventure trips",
            "💰 Budget-friendly options",
            "✈️ How to book?",
            "📦 Popular packages"
        ]
        
        if context:
            context_lower = context.lower()
            if 'paris' in context_lower or 'europe' in context_lower:
                return [
                    "Paris packages",
                    "Best time to visit",
                    "London trips",
                    "Barcelona tours",
                    "How to book?"
                ]
            elif 'tokyo' in context_lower or 'japan' in context_lower or 'asia' in context_lower:
                return [
                    "Tokyo packages",
                    "Bali beaches",
                    "Dubai luxury",
                    "Best time to visit",
                    "How to book?"
                ]
            elif 'beach' in context_lower or 'tropical' in context_lower:
                return [
                    "Bali packages",
                    "Maldives trips",
                    "Hawaii tours",
                    "Miami beaches",
                    "Budget options"
                ]
        
        return default_replies

    def generate_description(self, name, country, description_type='destination', additional_context=''):
        """
        Generate engaging travel description with enhanced prompting
        
        Args:
            name: Name of the destination/package
            country: Country where the destination is located
            description_type: Type of content ('destination' or 'package')
            additional_context: Any additional context to include
        
        Returns:
            dict with 'success' boolean and 'description' or 'error' string
        """
        if not self.initialized or not self.client:
            return {
                'success': False,
                'error': 'AI service is currently unavailable. Please try again later.'
            }
        
        if not name or not country:
            return {
                'success': False,
                'error': 'Please provide both destination name and country.'
            }
        
        prompt = f"""You are a professional travel copywriter. Write a compelling description for:

Destination: {name}, {country}
Purpose: {description_type.title()} listing on a travel booking website

Requirements:
- 2-3 engaging sentences (100-150 words)
- Highlight main attractions and unique experiences
- Include emotional appeal (adventure, relaxation, culture)
- Use vivid, sensory language
- Target: travelers seeking authentic experiences
- Tone: Enthusiastic but professional

{f'Additional Context: {additional_context}' if additional_context else ''}

Write ONLY the description, no preamble or labels."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional travel copywriter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=250
            )
            
            if response and response.choices and len(response.choices) > 0:
                
                description = response.choices[0].message.content.strip()
                
                
                preambles = ['Here is', 'Here\'s', 'Description:', 'Sure!', 'Certainly!']
                for preamble in preambles:
                    if description.lower().startswith(preamble.lower()):
                        lines = description.split('\n')
                        if len(lines) > 1:
                            description = '\n'.join(lines[1:]).strip()
                        break
                
                
                description = description.replace('**', '').replace('*', '')
                
                return {
                    'success': True,
                    'description': description
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not generate description. Please try again.'
                }
                
        except Exception as e:
            print(f"Description generation error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Error generating description: {str(e)}'
            }
    def recommend_packages(self, preferences, available_packages):
        """
        Recommend top 3 packages using RAG approach with Groq
        
        Args:
            preferences: dict with user preferences (min_budget, max_budget, interests, etc.)
            available_packages: list of package dicts from database
        
        Returns:
            list of dicts with package_id, match_score, and reasoning
        """
        if not self.initialized or not self.client:
            return []
            
        
        
        packages_context = "\n".join([
            f"ID: {p.get('package_id', p.get('id', 'N/A'))} | "
            f"Name: {p.get('package_name', p.get('name', 'N/A'))} | "
            f"Destination: {p.get('destination_name', p.get('destination', 'N/A'))} | "
            f"Price: ${p.get('economy_adult_price', p.get('adult_price', p.get('price', 'N/A')))} | "
            f"Duration: {p.get('duration_days', p.get('duration', 'N/A'))} days | "
            f"Description: {p.get('description', 'N/A')[:100]}..."
            for p in available_packages[:25] 
        ])
        
        prompt = f"""You are a travel recommendation expert. Based on user preferences, recommend the TOP 3 most suitable packages from the provided list.

USER PREFERENCES:
- Budget Range: ${preferences.get('min_budget', '0')} - ${preferences.get('max_budget', 'Flexible')}
- Interests: {', '.join(preferences.get('interests', ['Any']))}
- Travel Month: {preferences.get('month', 'Flexible')}
- Duration: {preferences.get('duration', 'Any')} days
- Travelers: {preferences.get('travelers', 1)} person(s)

AVAILABLE PACKAGES:
{packages_context}

TASK:
1. Analyze each package against user preferences.
2. Select the TOP 3 best matches.
3. If fewer than 3 packages are available, return all of them.

RESPONSE FORMAT (JSON only):
{{
  "recommendations": [
    {{
      "package_id": <id>,
      "match_score": <1-100>,
      "reasoning": "<2-3 sentences explaining why this package fits the user's preferences>"
    }}
  ]
}}

Rules:
- Match score represents alignment with budget and interests.
- Reasoning must be persuasive and reference specific user interests.
- Return ONLY the JSON object.
"""

        try:
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a travel recommendation expert who exclusively responds in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            import json
            result_text = response.choices[0].message.content.strip()
            
            
            recommendations_data = json.loads(result_text)
            return recommendations_data.get('recommendations', [])
            
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_booking_intent(self, user_query):
        """
        Extract booking parameters from natural language using Groq function calling
        """
        if not self.initialized or not self.client:
            return None
            
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "extract_travel_booking_params",
                    "description": "Extract travel booking parameters from a natural language query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination_type": {
                                "type": "string",
                                "enum": ["Beach", "Mountain", "City", "Desert", "Island", "Cultural", "Adventure", "Any"],
                                "description": "Type of destination the user wants to visit"
                            },
                            "destination_name": {
                                "type": "string",
                                "description": "Specific destination name if mentioned (e.g., 'Paris', 'Bali')"
                            },
                            "duration_days": {
                                "type": "integer",
                                "description": "Number of days for the trip"
                            },
                            "adults": {
                                "type": "integer",
                                "description": "Number of adult travelers",
                                "minimum": 1
                            },
                            "children": {
                                "type": "integer",
                                "description": "Number of child travelers",
                                "minimum": 0
                            },
                            "infants": {
                                "type": "integer",
                                "description": "Number of infant travelers",
                                "minimum": 0
                            },
                            "max_budget": {
                                "type": "number",
                                "description": "Maximum budget per person in USD"
                            },
                            "preferred_month": {
                                "type": "string",
                                "description": "Preferred travel month (e.g., 'June', 'December')"
                            },
                            "interests": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Travel interests or activities mentioned"
                            }
                        },
                        "required": ["destination_type", "adults"]
                    }
                }
            }
        ]
        
        try:
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a travel booking assistant. Extract booking parameters from user queries using the provided tool."
                    },
                    {
                        "role": "user",
                        "content": user_query
                    }
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "extract_travel_booking_params"}},
                temperature=0.1
            )
            
            
            message = response.choices[0].message
            
            if message.tool_calls:
                
                function_call = message.tool_calls[0]
                arguments = json.loads(function_call.function.arguments)
                
                
                result = {
                    'destination_type': arguments.get('destination_type', 'Any'),
                    'destination_name': arguments.get('destination_name', ''),
                    'duration_days': arguments.get('duration_days'),
                    'adults': arguments.get('adults', 1),
                    'children': arguments.get('children', 0),
                    'infants': arguments.get('infants', 0),
                    'max_budget': arguments.get('max_budget'),
                    'preferred_month': arguments.get('preferred_month', ''),
                    'interests': arguments.get('interests', [])
                }
                
                return result
            else:
                return None
                
        except Exception as e:
            print(f"Error extracting booking intent: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_search_summary(self, query, extracted_params, num_results):
        """
        Generate a natural language summary of search results
        """
        if not self.initialized or not self.client:
            return f"I found {num_results} packages matching your request!"
            
        try:
            prompt = f"""User asked: "{query}"

We extracted these parameters:
- Destination: {extracted_params.get('destination_type', 'Any')} {extracted_params.get('destination_name', '')}
- Duration: {extracted_params.get('duration_days', 'flexible')} days
- Travelers: {extracted_params.get('adults', 0)} adults, {extracted_params.get('children', 0)} children
- Budget: ${extracted_params.get('max_budget', 'flexible')} per person

We found {num_results} matching packages.

Step 1: Write a professional and helpful response in 2-3 sentences.
Step 2: Acknowledge what was understood.
Step 3: Point them to the results shown below.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional travel assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Summary generation error: {e}")
            return f"I found {num_results} packages matching your request!"

    def summarize_reviews(self, reviews, package_name):
        """
        Summarize multiple reviews into key insights using Groq
        """
        if not self.initialized or not self.client:
            return {
                'summary': 'No reviews yet. Be the first to share your experience!',
                'sentiment': 'neutral',
                'key_points': []
            }
      
        if not reviews or len(reviews) == 0:
            return {
                'summary': 'No reviews yet. Be the first to share your experience!',
                'sentiment': 'neutral',
                'key_points': []
            }   
        
        if len(reviews) <= 2:
            return {
                'summary': f"Based on {len(reviews)} initial rating(s). Not enough data for AI deep-dive.",
                'sentiment': 'neutral',
                'key_points': [f"Recent Customer Rating: {r['rating']}/5" for r in reviews],
                'pros': ["Growing interest"], 'cons': []
            }
        
        
        avg_rating = sum(float(r['rating']) for r in reviews) / len(reviews)
        ratings_chart = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in reviews:
            ratings_chart[int(r['rating'])] += 1
            
        prompt = f"""You are analyzing customer satisfaction for "{package_name}" based on numerical ratings.
        
REVIEWS DATA:
Total Ratings: {len(reviews)}
Average Score: {avg_rating:.1f}/5
Distribution:
- 5 Stars: {ratings_chart[5]}
- 4 Stars: {ratings_chart[4]}
- 3 Stars: {ratings_chart[3]}
- 2 Stars: {ratings_chart[2]}
- 1 Star: {ratings_chart[1]}

TASK:
Provide a concise psychological summary of customer sentiment based strictly on this rating distribution. 
For example, if most are 5-star, it's "highly reliable". If there's a lot of 1-star, it "needs immediate improvement".

RESPONSE FORMAT (Strict JSON only):
{{
  "summary": "<2-3 sentence overall sentiment analysis>",
  "sentiment": "<positive|mixed|negative>",
  "key_points": [
    "<statistical highlight 1>",
    "<statistical highlight 2>",
    "<statistical highlight 3>"
  ],
  "pros": ["<what high ratings imply>", "Great consistency"],
  "cons": ["<what lower ratings suggest>", "Potential areas for refinement"]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful travel review analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            summary_data = json.loads(response.choices[0].message.content)
            
            
            summary_data['total_reviews'] = len(reviews)
            summary_data['avg_rating'] = round(avg_rating, 1)
            
            return summary_data
            
        except Exception as e:
            print(f"Error summarizing reviews: {e}")
            return {
                'summary': f"Based on {len(reviews)} reviews (avg {avg_rating:.1f}/5). Check individual reviews for details.",
                'sentiment': 'mixed',
                'key_points': [],
                'total_reviews': len(reviews),
                'avg_rating': round(avg_rating, 1)
            }



chatbot_instance = TravelChatbot()


def get_chatbot():
    """Get the chatbot instance"""
    return chatbot_instance
