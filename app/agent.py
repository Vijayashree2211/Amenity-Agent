# agent.py
import os
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain_openai import OpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from utils.email_sender import send_booking_email
from utils.db import SessionLocal, Booking


class AmenityAgent:
    FIELDS = ["greet", "community", "amenity", "slot", "email"]

    FIELD_PROMPTS = {
        "greet": "Hi! Welcome to Amenity Booking 👋 Tell me which community you belong to.",
        "amenity": "What amenity would you like to book?",
        "slot": "Select a time slot from the available options:",
        "email": "Please provide your email address to confirm."
    }

    def __init__(self):
        self.llm = OpenAI(temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.memory = {}
        self.communities, self.synonyms, self.schedules = self._load_kb("kb/amenities_kb.txt")
        self.vector_store_path = "vector_store/amenity_kb_index"
        self.retriever = self._build_retriever()
        self.qa = RetrievalQA.from_chain_type(llm=self.llm, retriever=self.retriever)

    def _load_kb(self, path):
        communities, synonyms, schedules = {}, {}, {}
        current_community = None

        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Community:"):
                    current_community = line.split(":", 1)[1].strip()
                    communities[current_community] = []
                    schedules[current_community] = {}
                elif line.startswith("Amenities:"):
                    amenities = [a.strip() for a in line.split(":", 1)[1].split(",")]
                    communities[current_community].extend(amenities)
                elif line.startswith("Schedule:"):
                    parts = line.replace("Schedule:", "").strip().split("|")
                    if len(parts) == 2:
                        amenity = parts[0].strip()
                        times = [t.strip() for t in parts[1].split(",")]
                        schedules[current_community][amenity] = times
                elif "=" in line:
                    key, val = line.split("=")
                    synonyms[key.strip().lower()] = [v.strip().lower() for v in val.split(",")]

        return communities, synonyms, schedules

    def _build_retriever(self):
        if os.path.exists(self.vector_store_path):
            return FAISS.load_local(self.vector_store_path, self.embeddings, allow_dangerous_deserialization=True).as_retriever()

        docs = []
        for field in self.FIELDS:
            docs.append(Document(page_content=self.FIELD_PROMPTS.get(field, ""), metadata={"stage": field}))

        for community in self.communities:
            docs.append(Document(page_content=f"I live in {community}", metadata={"stage": "community"}))

        for community, amenities in self.communities.items():
            for amenity in amenities:
                docs.append(Document(page_content=f"Book {amenity}", metadata={"stage": "amenity"}))
                for key, synonyms in self.synonyms.items():
                    if amenity.lower() in [s.lower() for s in synonyms]:
                        docs.append(Document(page_content=f"Book {key}", metadata={"stage": "amenity"}))

        vectorstore = FAISS.from_documents(docs, self.embeddings)
        vectorstore.save_local(self.vector_store_path)
        return vectorstore.as_retriever()

    def handle_message(self, session_id, user_input):
        if session_id not in self.memory:
            self.memory[session_id] = {
                "stage": self.FIELDS[0],
                "data": {},
                "history": []
            }

        state = self.memory[session_id]
        current_stage = state["stage"]
        state["history"].append({"role": "user", "message": user_input})

        if current_stage == "greet":
            cleaned_input = user_input.strip().lower()
            matched = next((c for c in self.communities if c.lower() == cleaned_input), None)
            if matched:
                state["data"]["community"] = matched
                state["stage"] = "amenity"
                return self.FIELD_PROMPTS["amenity"]
            return self.FIELD_PROMPTS["greet"]

        if current_stage == "amenity":
            community = state["data"].get("community")
            amenities = self.communities.get(community, [])
            user_lower = user_input.strip().lower()
            matched = next((a for a in amenities if a.lower() == user_lower), None)
            if not matched:
                for key, values in self.synonyms.items():
                    all_synonyms = [key.lower()] + [v.lower() for v in values]
                    if user_lower in all_synonyms:
                        matched = next((a for a in amenities if a.lower() == key.lower() or a.lower() in [v.lower() for v in values]), None)
                        if matched:
                            break
            if not matched:
                return f"Amenity not available in {community}. Try another."
            state["data"]["amenity"] = matched
            state["stage"] = "slot"
            slots = self.schedules.get(community, {}).get(matched, [])
            if not slots:
                return f"No available slots for {matched} in {community}."
            return {
                "type": "slot_selection",
                "message": f"Available time slots for {matched} in {community}:",
                "slots": slots
            }

        if current_stage == "slot":
            community = state["data"].get("community")
            amenity = state["data"].get("amenity")
            slots = self.schedules.get(community, {}).get(amenity, [])
            selected = user_input.strip()
            if selected not in slots:
                return {
                    "type": "slot_selection",
                    "message": f"Invalid slot. Please select one of these for {amenity}:",
                    "slots": slots
                }
            state["data"]["slot"] = selected
            state["stage"] = "email"
            return self.FIELD_PROMPTS["email"]

        if current_stage == "email":
            state["data"]["email"] = user_input
            send_booking_email(
                state["data"]["email"],
                state["data"]["community"],
                state["data"]["amenity"],
                state["data"]["slot"],
                state["data"]["slot"]
            )
            db = SessionLocal()
            slot = state["data"].pop("slot", "")
            state["data"]["slot"] = slot

            db.add(Booking(**state["data"]))
            db.commit()
            db.close()
            self.memory.pop(session_id)
            return f"✅ Booking confirmed for {state['data']['amenity']} in {state['data']['community']} at {state['data']['slot']}! Confirmation sent to {state['data']['email']}."

        return f"Sorry, I didn't catch that. {self.FIELD_PROMPTS[current_stage]}"

    def get_history(self, session_id):
        return self.memory.get(session_id, {}).get("history", [])
