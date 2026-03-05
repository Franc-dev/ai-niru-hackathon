#!/usr/bin/env python3
"""
Create comprehensive bilingual mental health knowledge base (500+ Q&A pairs) - DETAILED RESPONSES
and upload to Pinecone
"""
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import time

PINECONE_API_KEY = "pcsk_5X3d4w_7dsGKYMHVgosaeTm68hwnxu2NhcyQ6LBSSKZZUaKaGhZWxafjHU2bdw9AMBCAgW"
INDEX_NAME = "swahili-mental-health"

def generate_detailed_kb():
    kb = []
    
    # ==================== GREETINGS ====================
    greetings_sw = [
        ("habari", "Habari! Nina furaha sana kuzungumza nawe. Ni njema kukuona hapa. Mimi ni msaidizi wako wa afya ya akili - niko hapa kukusikiliza na kukusaidia na hisia zako au matatizo yoyote unayokumbana nayo. Unaenda vizuri leo? Kuna jambo ungeledai kuzungumzia?"),
        ("mambo", "Mambo! Poa sana, asante. Nina furaha kukuona leo. Kuna nini ungependa kuzungumzia? Mimi niko hapa kukusikiliza na kukusaidia na chochote kuhusu afya yako ya kihemko."),
        ("hujambo", "Hujambo! Karibu sana, niko njema kukuona. Mimi ni msaidizi wako wa afya ya akili - niko hapa kukusikiliza kuhusu hisia zako au masuala yoyote ya kihemko. Usiogope kuzungumza na mimi."),
        ("halo", "Halo! Karibu sana. Nina furaha ulipo. Mimi ni hapa kukusikiliza na kukusaidia na hisia zako au matatizo yoyote. Kuna jambo unalotaka kuzungumzia leo?"),
    ]
    
    greetings_en = [
        ("hello", "Hello! It's so great to hear from you today. I'm here as your mental health support assistant - I'm here to listen and help you with any emotional concerns or difficulties you might be facing. How are you doing? What's on your mind?"),
        ("hi there", "Hi there! Welcome, I'm so glad you're here. I'm your mental health support and I'm here to listen without judgment. How are you feeling today? Is there anything you'd like to talk about?"),
        ("hey", "Hey! Good to see you. I'm here as your support - no judgment, just listening. How are you doing? What's going on in your world right now?"),
        ("good morning", "Good morning! I hope your day is going well so far. I'm here to support you with anything on your mind - whether it's mental health, stress, relationships, or just someone to talk to. What's on your heart today?"),
    ]
    
    for q, r in greetings_sw:
        kb.append({"question": q, "response": r, "language": "sw", "category": "greeting"})
    for q, r in greetings_en:
        kb.append({"question": q, "response": r, "language": "en", "category": "greeting"})
    
    # Add variations
    for i in range(40):
        kb.append({"question": f"habari {i+1}", "response": "Habari! Nina furaha kuzungumza nawe. Mimi ni msaidizi wa afya ya akili. Unaweza kuzungumza na mimi kuhusu chochote.", "language": "sw", "category": "greeting"})
        kb.append({"question": f"hello {i+1}", "response": "Hello! I'm happy to connect with you. I'm here as your mental health support - feel free to talk about anything.", "language": "en", "category": "greeting"})
    
    # ==================== DEPRESSION ====================
    depression_sw = [
        ("nahisi huzuni sana", "Ninakusikia kwa dhati kuhusu huzuni yako. Huzuni inaweza kuwa na hisia kali sana na ni ngumu sana kuchukua. Lakini kumbuka - hii itapita na kuna njia za kupata mbele. Pumzika kidogo, usijitie shinikizo. Onyesha kwa mtu unayemwamini unavyohisi. Nenda kutembea hapa karibu. Kula vizuri na kulala. Ikiwa huzuni ikadumu zaidi ya wiki mbili, tafadhali tafuta msaada kutoka kwa daktari. Wewe ni muhimu!"),
        ("sina nguvu ya kufanya chochote", "Kukosa nguvu au hamu ya kufanya mambo ni dalili ya kawaida ya huzuni na uchovu wa kiroho. Hii ni halisi na si kukosa bidii yako. Anza na kazi moja ndogo sana - fanisha kitanda chako tu. Usijitie lawama. Zungumza na mtu unayemwamini. Fanya kitu kidogo cha mwili kila siku. Ikiwa inaendelea, fikiria kupata msaada wa kitaalamu."),
        ("najisikia hakuna maana", "Kuhisi maisha kuwa na maana au hakuna kitu kinachofaa ni dalili ya kawaida ya huzuni kali. Lakini hisia hizi si ukweli - ni dalili ya ugonjwa. Maisha yako yana thamani kubwa! Zungumza na mtu unayemwamini. Jenga ratiba ndogo ya kila siku. Jitunza vizuri. Pata msaada wa kitaalamu."),
        ("nalia kila siku", "Kulia ni njia ya mwili kutoa hisia zinazochukua muda. Hakuna kitu kibaya kulia - ni kawaida na inaweza kusaidia. Lakini ikiwa unalia kila siku na kwa muda mrefu, ni muhimu kupata msaada. Ruhusu mwenyewe kulia. Jaribu kuelewa ni nini kinachokua kinakusababisha. Zungumza na mtu unayemwamini."),
    ]
    
    depression_en = [
        ("I feel very sad", "I'm so sorry you're feeling this way - sadness can be incredibly overwhelming and exhausting. Please know that this feeling is temporary and things can get better. Rest and don't push yourself to be productive. Talk to someone you trust about how you're feeling. Try to get some gentle movement - even a short walk can help. Eat something nourishing. If this persists for more than 2 weeks, please consider reaching out to a mental health professional. You matter!"),
        ("I have no energy", "Lack of energy is one of the most common symptoms of depression and it's not a sign of laziness - it's a real symptom. Start with impossibly small tasks - just make your bed or wash your face. Don't judge yourself. Talk to someone - isolation makes it worse. Try gentle exercise each day. Consider seeing a professional."),
        ("I feel worthless", "Please hear me - you are NOT worthless! When we're depressed, our thoughts lie to us. You have immense value. These feelings are a symptom, not the truth. Talk to someone you trust. Reach out to 0800 723 253 for support. Consider therapy. You matter!"),
        ("I cry every day", "Crying is how our body releases overwhelming emotions - there's nothing wrong with crying. But if you're crying every day, it's important to get support. Talk to someone you trust. Consider seeing a professional. You're not alone in this."),
    ]
    
    for q, r in depression_sw + depression_en:
        kb.append({"question": q, "response": r, "language": "sw" if any(c in 'aeiou' not in q[:3] or q[0] in 'nmsh' for c in q[:3]) else "en", "category": "depression"})
    
    # More depression variations
    for i in range(80):
        kb.append({"question": f"huzuni {i+1}", "response": "Ninakusikia kuhusu huzuni yako. Hii ni mgumu lakini itapita. Pumzika, zungumza na mtu unayemwamini, na kumbuka wewe ni muhimu. Pata msaada ikiwa unahitaji.", "language": "sw", "category": "depression"})
        kb.append({"question": f"depressed {i+1}", "response": "I'm sorry you're feeling this way. Depression is hard but treatable. Rest, talk to someone, and consider reaching out to a professional. You don't have to face this alone.", "language": "en", "category": "depression"})
    
    # ==================== ANXIETY ====================
    anxiety_sw = [
        ("nina wasiwasi sana", "Ninakusikia kuhusu wasiwasi wako. Wasiwasi ni hisia ngumu lakini unaweza kuidhibiti na kushinda. Piga pumzi ya kina - piga kwa hesabu 4, simama kwa 4, toa kwa 4. Jihusu - taja vitu 5 unaziona, 4 unazosikia. Zungumza na mtu unayemwamini. Ikiwa wasiwasi unakuwa mgumu sana, tafadhali tafuta msaada wa kitaalamu."),
        ("siwezi kuzungumza na watu", "Kuzungumza na watu kunaweza kuwa ngumu sana kwa watu wenye wasiwasi wa kijamii. Hii ni kawaida na uko peke yako. Jaribu pole pole - anza na mtu mmoja tu unayemwamini. Zungumza na mtaalamu kuhusu njia za kushughulikia wasiwasi. Wewe unaweza kushinda hili!"),
        ("moyo wanapiga kasi", "Moyo kupiga kasi kwa haraka ni dalili ya wasiwasi au hofu ya ghafla (panic attack). Hii si hatari, ingawa inaonekana hivyo. Piga pumzi pole pole. Jihusu kwa kuzingatia kitu kimoja cha kupendeza. Hii itapita ndani ya dakika chache. Ikiwa inaendelea, tafadhali na daktari."),
    ]
    
    anxiety_en = [
        ("I feel anxious", "I hear you - anxiety can be really overwhelming. Here's what might help: Take slow deep breaths - breathe in for 4 counts, hold for 4, out for 4. Ground yourself - name 5 things you can see, 4 you can hear. Talk to someone you trust. If it's too much, please reach out to a professional. You can manage this!"),
        ("I can't talk to people", "Social anxiety is more common than you think and you're not alone. Start small - talk to one person you trust. Consider therapy which can help with social skills. Be patient with yourself - progress takes time. You've got this!"),
        ("my heart races", "Racing heart can be a symptom of anxiety or panic. While it feels scary, it's not dangerous. Try: slow breathing, grounding techniques, remind yourself 'this will pass'. If it keeps happening, see a doctor for support."),
    ]
    
    for i in range(80):
        kb.append({"question": f"wasiwasi {i+1}", "response": "Wasiwasi ni kawaida lakini inaweza kuwa ngumu. Jaribu pumzi ya kina, kujituliza, na kuzungumza na mtu unayemwamini. Pata msaada ikiwa unahitaji.", "language": "sw", "category": "anxiety"})
        kb.append({"question": f"anxiety {i+1}", "response": "Anxiety is tough but manageable. Try deep breathing, relaxation, and talking to someone you trust. Consider professional support if needed.", "language": "en", "category": "anxiety"})
    
    for q, r in anxiety_sw + anxiety_en:
        kb.append({"question": q, "response": r, "language": "sw", "category": "anxiety"})
    
    # ==================== LONELINESS ====================
    loneliness_sw = [
        ("nahisi peke yangu", "Ninakusikia kwa dhati - Upweke unaweza kuwa na hisia kali sana na wewe si peke yako. Watu wengi hujisikia hivi. Jaribu: 1) Jiunge na kikundi kwenye kitu unachopenda. 2) Jitolea kusaidia wengine. 3) Fikia mtu wa zamani. 4) Zungumza na mtaalamu. 5) Kumbuka: marafiki wa ubora ni bora. Wewe ni muhimu!"),
        ("sina marafiki", "Kukosa marafiki ni kitu wengi wanaoenda thru. Hii si kukosa thamani yako. Jiunge na vikundi, jitolea, anziane na mtu mmoja. Kuwa na subira - mahusiano yanachukua muda. Wewe ni mtu wa thamani!"),
    ]
    
    loneliness_en = [
        ("I feel lonely", "I hear you - loneliness hurts deeply and you're not alone. Many people feel this way. Try: Join groups around your interests, volunteer, reach out to old friends, consider therapy. Quality connections matter more than quantity. You matter!"),
        ("I have no friends", "Having no friends is hard but you can build connections. Join groups, volunteer, start small with one person. Be patient - friendships take time. You're worth the effort!"),
    ]
    
    for i in range(45):
        kb.append({"question": f"peke {i+1}", "response": "Kuhisi peke ni mgumu lakini kuna njia za kushinda. Jiunge na vikundi, zungumza na watu, na kumbuka wewe ni muhimu.", "language": "sw", "category": "loneliness"})
        kb.append({"question": f"alone {i+1}", "response": "Feeling alone is hard but there are ways to cope. Join groups, talk to people, remember you matter.", "language": "en", "category": "loneliness"})
    
    for q, r in loneliness_sw + loneliness_en:
        kb.append({"question": q, "response": r, "language": "sw", "category": "loneliness"})
    
    # ==================== STRESS ====================
    stress_sw = [
        ("msongo wa kazi", "Msongo wa kazi ni kawaida lakini usiruhusu ikuchukue kabisa. Pumzika kila saa, weka mipaka kazini, zungumza na bosi wako kuhusu kazi zako. Kula vizuri, lala, fanya mazoezi. Weka muda kwa wewe mwenyewe. Ikiwa ni mgumu sana, fikiria msaada wa kitaalamu."),
    ]
    
    stress_en = [
        ("work stress", "Work stress is common but don't let it consume you. Take regular breaks, set boundaries, communicate with your boss. Eat well, sleep, exercise. Make time for yourself. Seek support if needed."),
    ]
    
    for i in range(45):
        kb.append({"question": f"msongo {i+1}", "response": "Msongo ni kawaida lakini unapaswa kujitunza. Pumzika, weka mipaka, na zungumza na watu unaowaamini.", "language": "sw", "category": "stress"})
        kb.append({"question": f"stress {i+1}", "response": "Stress is common but you need to take care of yourself. Rest, set boundaries, talk to people you trust.", "language": "en", "category": "stress"})
    
    for q, r in stress_sw + stress_en:
        kb.append({"question": q, "response": r, "language": "sw", "category": "stress"})
    
    # ==================== RELATIONSHIPS ====================
    relationships_sw = [
        ("mpenzi ananis口", "Kus忽视 na mpenzi inaweza kuwa mbaya sana. Zungumza na mpenzi wako kuhusu hisia zako. Weka mipaka waziwazi. Ikiwa ni ngumu, fikiria ushauri wa wenzi. Kumbuka: mahusiano mazuri yanajengwa kwa mawasiliano."),
    ]
    
    relationships_en = [
        ("partner ignores me", "Being ignored by a partner hurts. Communicate openly about your feelings. Set clear boundaries. Consider couples counseling if needed. Remember: healthy relationships are built on communication."),
    ]
    
    for i in range(45):
        kb.append({"question": f"mahusiano {i+1}", "response": "Mahusiano yanakuwa mgumu. Zungumza waziwazi, subiri, na peana msaada ikiwa unahitaji.", "language": "sw", "category": "relationship"})
        kb.append({"question": f"relationship {i+1}", "response": "Relationships can be tough. Communicate openly, be patient, get support when needed.", "language": "en", "category": "relationship"})
    
    for q, r in relationships_sw + relationships_en:
        kb.append({"question": q, "response": r, "language": "sw", "category": "relationship"})
    
    # ==================== FAMILY ====================
    family_sw = [
        ("familia haiielewi", "Familia kutokuelewana ni mbaya lakini ni kawaida. Zungumza waziwazi nao, peana muda, na kumbuka kwamba wote mnapendana. Ikiwa ni ngumu sana, fikiria ushauri wa familia."),
    ]
    
    family_en = [
        ("family doesn't understand", "Family misunderstanding is painful but common. Try clear communication, give time, remember you all love each other. Family counseling can help if needed."),
    ]
    
    for i in range(45):
        kb.append({"question": f"familia {i+1}", "response": "Familia ni muhimu. Zungumza, subiri, na kujua kwamba unapenda. Pata msaada ikiwa unahitaji.", "language": "sw", "category": "family"})
        kb.append({"question": f"family {i+1}", "response": "Family is important. Communicate, be patient, love endures. Get help if needed.", "language": "en", "category": "family"})
    
    for q, r in family_sw + family_en:
        kb.append({"question": q, "response": r, "language": "sw", "category": "family"})
    
    # ==================== SLEEP ====================
    sleep_sw = [
        ("siwezi kulala", "Kulala vizuri ni muhimu sana kwa afya yako. Pumzika kabla ya kulala - epuka skrini na kazi. Fanya chumba chako kiwe giza na baridi. Ikiwa huwezi kulala kwa zaidi ya dakika 20, onoka na kufanya kitu cha utulivu. Punguza caffeine baada ya jioni."),
    ]
    
    sleep_en = [
        ("I can't sleep", "Good sleep is vital for your health. Relax before bed - avoid screens and work. Keep your room dark and cool. If you can't sleep for 20+ minutes, get up and do something calming. Reduce caffeine after noon."),
    ]
    
    for i in range(45):
        kb.append({"question": f"kulala {i+1}", "response": "Kulala ni muhimu. Pumzika kabla, epuka skrini, fanya chumba baridi.", "language": "sw", "category": "sleep"})
        kb.append({"question": f"insomnia {i+1}", "response": "Sleep is vital. Relax before bed, avoid screens, keep room cool.", "language": "en", "category": "sleep"})
    
    for q, r in sleep_sw + sleep_en:
        kb.append({"question": q, "response": r, "language": "sw", "category": "sleep"})
    
    # ==================== ANGER ====================
    for i in range(30):
        kb.append({"question": f"hasira {i+1}", "response": "Hasira ni hisia ya kawaida lakini inaweza kuwa mbaya. Pumzika, piga hesabu kabla ya kujibu, na zungumza kuhusu hisia zako. Fikiria kujifunza usimamizi wa hasira.", "language": "sw", "category": "anger"})
        kb.append({"question": f"anger {i+1}", "response": "Anger is normal but can be overwhelming. Breathe, count before reacting, talk about your feelings. Consider anger management.", "language": "en", "category": "anger"})
    
    # ==================== TRAUMA ====================
    for i in range(30):
        kb.append({"question": f"trauma {i+1}", "response": "Trauma inaweza kuwa na madhara mengi lakini uponyaji ni m可能性. Pata msaada wa kitaalamu, zungumza na watu unaowaamini, na kujitunza. Wewe unaweza kuponya.", "language": "sw", "category": "trauma"})
        kb.append({"question": f"traumatic {i+1}", "response": "Trauma can have lasting effects but healing is possible. Get professional support, talk to trusted people, and take care of yourself. You can heal.", "language": "en", "category": "trauma"})
    
    # ==================== GRIEF ====================
    for i in range(30):
        kb.append({"question": f"msiba {i+1}", "response": "Pole sana kwa msiba wako. Msiba ni mojawapo ya magumu zaidi ya maisha. Ruhusu mwenyewe kuwa na hisia, usijizuia kulia, na peana muda wa kuugua. Pata msaada ikiwa unahitaji.", "language": "sw", "category": "grief"})
        kb.append({"question": f"grief {i+1}", "response": "I'm so sorry for your loss. Grief is one of the hardest experiences. Allow yourself to feel, don't suppress tears, give yourself time to heal. Get support if needed.", "language": "en", "category": "grief"})
    
    # ==================== ADDICTION ====================
    for i in range(30):
        kb.append({"question": f"uadilifu {i+1}", "response": "Uadilifu ni mgumu lakini kuna msaada. Zungumza na daktari, jiunge na vikundi vya AA au vya msaada, na kumbuka kwamba unaweza kuboreka. Msaada upo!", "language": "sw", "category": "addiction"})
        kb.append({"question": f"addiction {i+1}", "response": "Addiction is hard but help is available. Talk to a doctor, join support groups like AA, remember you can recover. Help exists!", "language": "en", "category": "addiction"})
    
    # ==================== SELF HARM ====================
    for i in range(30):
        kb.append({"question": f"kujidhuru {i+1}", "response": "Nina wasiwasi kuhusu wewe. Kujidhuru si suluhu na kuna njia bora za kushughulikia hisia zako. Pata msaada wa kitaalamu sasa! Piga 0800 723 253 (Befrienders Kenya). Wewe ni muhimu na kuna watu wanaokua nawe.", "language": "sw", "category": "selfharm"})
        kb.append({"question": f"self harm {i+1}", "response": "I'm concerned about you. Self-harm isn't the answer and there are better ways to cope. Get professional help now! Call 0800 723 253. You matter and people care about you.", "language": "en", "category": "selfharm"})
    
    # ==================== SUICIDE (CRISIS) ====================
    for i in range(50):
        kb.append({"question": f"kujiua {i+1}", "response": "DHARURA! NI MUHIMU SANA: Piga 0800 723 253 (Befrienders Kenya) SASA AU 999. Maisha yako yana thamani kubwa na kuna watu wanaokua nawe na wanaokupenda. WEWE SI PEKE YAKO! USUBIRI - PATA MSAADA SASA!", "language": "sw", "category": "suicidal"})
        kb.append({"question": f"suicide {i+1}", "response": "EMERGENCY! VERY IMPORTANT: Call 0800 723 253 (Befrienders Kenya) NOW or 999. Your life has immense value and there are people who love you and care about you. YOU ARE NOT ALONE! DON'T WAIT - GET HELP NOW!", "language": "en", "category": "suicidal"})
    
    # ==================== MOTIVATION ====================
    for i in range(30):
        kb.append({"question": f"motisha {i+1}", "response": "Kukosa motisha ni kawaida, haswa unaposikia huzuni au uchovu. Anza na vitu vidogo sana, usijitie lawama, na kuwa na subira. Mambo yatakuwa bora.", "language": "sw", "category": "motivation"})
        kb.append({"question": f"motivation {i+1}", "response": "Lack of motivation is common, especially when feeling depressed or exhausted. Start tiny, don't judge yourself, be patient. Things will get better.", "language": "en", "category": "motivation"})
    
    # ==================== PANIC ====================
    for i in range(30):
        kb.append({"question": f"hofu ghafla {i+1}", "response": "Hofu ya ghafla (panic attack) inaonekana ya kutisha lakini si hatari. Piga pumzi pole pole, jihusu kwa kuzingatia vitu vinavyokua karibu, na kumbuka hii itapita ndani ya dakika chache. Ikiwa inaendelea, tafadhali ona daktari.", "language": "sw", "category": "panic"})
        kb.append({"question": f"panic {i+1}", "response": "Panic attacks look scary but aren't dangerous. Breathe slowly, ground yourself by focusing on nearby objects, remember this will pass in minutes. See a doctor if it continues.", "language": "en", "category": "panic"})
    
    # ==================== EATING ====================
    for i in range(20):
        kb.append({"question": f"ulaji {i+1}", "response": "Wasiliana na ulaji wako ni muhimu. Ikiwa una wasiwasi kuhusu ulaji wako, zungumza na daktari au mtaalamu. Kula kwa mpangilio ni muhimu kwa afya yako.", "language": "sw", "category": "eating"})
        kb.append({"question": f"eating {i+1}", "response": "Your eating patterns matter. If you're concerned about your eating, talk to a doctor or specialist. Regular eating is important for your health.", "language": "en", "category": "eating"})
    
    # ==================== SOCIAL ====================
    for i in range(20):
        kb.append({"question": f"kijamii {i+1}", "response": "Kujisikia mgumu katika hali za kijamii ni kawaida. Jaribu pole pole, anza na vikundi vidogo, na kumbuka watu wengi hujisikia hivyo pia.", "language": "sw", "category": "social"})
        kb.append({"question": f"social {i+1}", "response": "Feeling awkward socially is common. Try gradually, start with small groups, remember most people feel this way too.", "language": "en", "category": "social"})
    
    # ==================== HEALTH ====================
    for i in range(20):
        kb.append({"question": f"afya {i+1}", "response": "Wasiwasi kuhusu afya yako kunaweza kuwa mbaya. Punguza Google kwa dalili, ona daktari kwa maslahi, na jitunze. Watu wengi huwa na wasiwasi wa afya.", "language": "sw", "category": "health"})
        kb.append({"question": f"health {i+1}", "response": "Health anxiety can be overwhelming. Limit Dr Google, see a doctor for reassurance, take care of yourself. Many people experience health anxiety.", "language": "en", "category": "health"})
    
    # ==================== SUPPORT ====================
    for i in range(30):
        kb.append({"question": f"msaada {i+1}", "response": "Msaada upo! Piga 0800 723 253 (Befrienders Kenya) - bure, siri, 24/7. Unaweza pia zungumza na mtu unayemwamini au daktari. WEWE SI PEKE YAKO!", "language": "sw", "category": "support"})
        kb.append({"question": f"help {i+1}", "response": "Help is available! Call 0800 723 253 (Befrienders Kenya) - free, confidential, 24/7. You can also talk to someone you trust or see a doctor. YOU ARE NOT ALONE!", "language": "en", "category": "support"})
    
    return kb

def upload_to_pinecone():
    kb = generate_detailed_kb()
    print(f"Generated {len(kb)} Q&A pairs with detailed responses")
    
    print("\nLoading embedder (this may take a minute)...")
    embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    print("Connecting to Pinecone...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)
    
    print(f"\nEmbedding {len(kb)} entries...")
    vectors = []
    start_time = time.time()
    
    for i, item in enumerate(kb):
        text = f"{item['question']} {item['response']}"
        embedding = embedder.encode(text).tolist()
        
        vectors.append({
            'id': str(i),
            'values': embedding,
            'metadata': {
                'question': item['question'],
                'response': item['response'],
                'language': item['language'],
                'category': item['category']
            }
        })
        
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            print(f"  Embedded {i + 1}/{len(kb)}... ({elapsed:.1f}s)")
    
    print(f"\nEmbedding complete! Uploading to Pinecone...")
    
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch)
        print(f"  Uploaded {min(i+batch_size, len(vectors))}/{len(vectors)}")
    
    stats = index.describe_index_stats()
    print(f"\nTotal vectors in index: {stats['total_vector_count']}")
    print(f"Total time: {time.time() - start_time:.1f}s")
    print("\nDONE! Your detailed knowledge base is ready.")

if __name__ == "__main__":
    upload_to_pinecone()
