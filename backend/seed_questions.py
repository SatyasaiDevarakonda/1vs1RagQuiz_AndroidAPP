"""
Seed database with sample questions
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"
DATABASE_NAME = "quiz_battle"

SAMPLE_QUESTIONS = [
    {
        "question": "What is the capital of France?",
        "options": ["London", "Berlin", "Paris", "Madrid"],
        "correct_answer": "Paris",
        "category": "Geography"
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "options": ["Venus", "Mars", "Jupiter", "Saturn"],
        "correct_answer": "Mars",
        "category": "Science"
    },
    {
        "question": "What is the largest mammal in the world?",
        "options": ["African Elephant", "Blue Whale", "Giraffe", "Hippopotamus"],
        "correct_answer": "Blue Whale",
        "category": "Science"
    },
    {
        "question": "Who painted the Mona Lisa?",
        "options": ["Michelangelo", "Leonardo da Vinci", "Raphael", "Donatello"],
        "correct_answer": "Leonardo da Vinci",
        "category": "Art"
    },
    {
        "question": "What is the chemical symbol for Gold?",
        "options": ["Go", "Gd", "Au", "Ag"],
        "correct_answer": "Au",
        "category": "Science"
    },
    {
        "question": "Which country has the largest population?",
        "options": ["India", "United States", "Indonesia", "China"],
        "correct_answer": "India",
        "category": "Geography"
    },
    {
        "question": "What year did World War II end?",
        "options": ["1943", "1944", "1945", "1946"],
        "correct_answer": "1945",
        "category": "History"
    },
    {
        "question": "What is the smallest prime number?",
        "options": ["0", "1", "2", "3"],
        "correct_answer": "2",
        "category": "Mathematics"
    },
    {
        "question": "Which element has the atomic number 1?",
        "options": ["Helium", "Hydrogen", "Lithium", "Carbon"],
        "correct_answer": "Hydrogen",
        "category": "Science"
    },
    {
        "question": "What is the largest ocean on Earth?",
        "options": ["Atlantic Ocean", "Indian Ocean", "Pacific Ocean", "Arctic Ocean"],
        "correct_answer": "Pacific Ocean",
        "category": "Geography"
    },
    {
        "question": "Who wrote 'Romeo and Juliet'?",
        "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
        "correct_answer": "William Shakespeare",
        "category": "Literature"
    },
    {
        "question": "What is the speed of light in vacuum?",
        "options": ["299,792 km/s", "150,000 km/s", "1,080 km/h", "343 m/s"],
        "correct_answer": "299,792 km/s",
        "category": "Science"
    },
    {
        "question": "Which programming language was created by Guido van Rossum?",
        "options": ["Java", "C++", "Python", "JavaScript"],
        "correct_answer": "Python",
        "category": "Technology"
    },
    {
        "question": "What is the capital of Japan?",
        "options": ["Seoul", "Beijing", "Tokyo", "Bangkok"],
        "correct_answer": "Tokyo",
        "category": "Geography"
    },
    {
        "question": "How many continents are there on Earth?",
        "options": ["5", "6", "7", "8"],
        "correct_answer": "7",
        "category": "Geography"
    },
    {
        "question": "What is the hardest natural substance on Earth?",
        "options": ["Gold", "Iron", "Diamond", "Platinum"],
        "correct_answer": "Diamond",
        "category": "Science"
    },
    {
        "question": "Who developed the theory of relativity?",
        "options": ["Isaac Newton", "Albert Einstein", "Stephen Hawking", "Niels Bohr"],
        "correct_answer": "Albert Einstein",
        "category": "Science"
    },
    {
        "question": "What is the main ingredient in guacamole?",
        "options": ["Tomato", "Avocado", "Lime", "Onion"],
        "correct_answer": "Avocado",
        "category": "Food"
    },
    {
        "question": "Which country is home to the kangaroo?",
        "options": ["New Zealand", "South Africa", "Australia", "Brazil"],
        "correct_answer": "Australia",
        "category": "Geography"
    },
    {
        "question": "What is the square root of 144?",
        "options": ["10", "11", "12", "14"],
        "correct_answer": "12",
        "category": "Mathematics"
    },
    {
        "question": "Who was the first person to walk on the Moon?",
        "options": ["Buzz Aldrin", "Neil Armstrong", "Yuri Gagarin", "John Glenn"],
        "correct_answer": "Neil Armstrong",
        "category": "History"
    },
    {
        "question": "What is the currency of the United Kingdom?",
        "options": ["Euro", "Dollar", "Pound Sterling", "Franc"],
        "correct_answer": "Pound Sterling",
        "category": "General"
    },
    {
        "question": "Which gas do plants absorb from the atmosphere?",
        "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"],
        "correct_answer": "Carbon Dioxide",
        "category": "Science"
    },
    {
        "question": "What is the largest planet in our solar system?",
        "options": ["Saturn", "Neptune", "Jupiter", "Uranus"],
        "correct_answer": "Jupiter",
        "category": "Science"
    },
    {
        "question": "Which company created the iPhone?",
        "options": ["Samsung", "Google", "Apple", "Microsoft"],
        "correct_answer": "Apple",
        "category": "Technology"
    },
    {
        "question": "What is the boiling point of water at sea level?",
        "options": ["90°C", "100°C", "110°C", "120°C"],
        "correct_answer": "100°C",
        "category": "Science"
    },
    {
        "question": "Which river is the longest in the world?",
        "options": ["Amazon", "Nile", "Yangtze", "Mississippi"],
        "correct_answer": "Nile",
        "category": "Geography"
    },
    {
        "question": "What year was the first iPhone released?",
        "options": ["2005", "2006", "2007", "2008"],
        "correct_answer": "2007",
        "category": "Technology"
    },
    {
        "question": "Who is the author of Harry Potter?",
        "options": ["J.R.R. Tolkien", "J.K. Rowling", "George R.R. Martin", "Stephen King"],
        "correct_answer": "J.K. Rowling",
        "category": "Literature"
    },
    {
        "question": "What is the chemical formula for water?",
        "options": ["CO2", "H2O", "NaCl", "O2"],
        "correct_answer": "H2O",
        "category": "Science"
    }
]


async def seed_database():
    """Seed the database with sample questions"""
    print("🌱 Seeding database...")
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DATABASE_NAME]
    
    try:
        # Clear existing questions
        await db.questions.delete_many({})
        
        # Insert questions
        result = await db.questions.insert_many(SAMPLE_QUESTIONS)
        
        print(f"✅ Inserted {len(result.inserted_ids)} questions")
        print(f"📊 Database: {DATABASE_NAME}")
        
        # Verify
        count = await db.questions.count_documents({})
        print(f"📝 Total questions in database: {count}")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
