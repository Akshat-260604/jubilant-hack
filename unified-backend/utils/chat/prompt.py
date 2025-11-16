CONTENT_FORMAT_prompt = {
    "clinical_summary": """
You are a clinical research summarizer AI. Your task is to generate a concise, structured clinical summary from the following medical or pharmaceutical document. The document may include clinical trial data, drug research, treatment protocols, or regulatory information.

Your summary should follow this structure:

1. **Study Title:**
2. **Sponsor and Investigators:**
3. **Study Period / Dates:**
4. **Study Design and Methodology:**
5. **Objectives:**
6. **Key Findings:**
7. **Conclusions:**
8. **Additional Notes (if any):**

Maintain a professional and scientific tone. Be factual and objective.
""",

    "clinical_trial_report": """
Generate a comprehensive clinical trial report from the given document. Include:
1. Study title, ID, and phase
2. Sponsor and investigator details
3. Study objectives (primary and secondary)
4. Methodology (design, randomization, controls, blinding)
5. Participant info (sample size, inclusion/exclusion)
6. Intervention details (dosage, administration)
7. Outcome measures and timepoints
8. Statistical analysis methods
9. Results (efficacy and safety)
10. Conclusion and recommendations

Use a regulatory-aligned, scientific tone.
""",

    "patient_case_study": """
Create a fictional patient case study inspired by the medical data. Include:
1. Patient background
2. Diagnosis and medical history
3. Treatment plan and process
4. Clinical response and follow-up
5. Key learnings or takeaways

Ensure anonymity and present the information as a narrative.
""",

    "plain_language_summary": """
Create a plain language summary of the medical content for a general audience. Include:
1. What the study or content is about
2. Why it matters
3. What happened
4. What was learned

Use simple, accessible language without medical jargon.
""",

    "email": """
Generate a professional email based on the user input, objective, and any provided context. Use the specified tone and write for the intended target audience. 
If using document excerpts (context), ensure they are factually accurate and directly relevant. 
Do not include any information not present in the input, objective, or context.

""",

    "pamphlet": """
Create content for a pamphlet summarizing the medical content. Include:
1. Title and purpose
2. Key takeaways
3. Benefits or outcomes
4. Contact or follow-up info

Use short headings, bullet points, and layperson-friendly language.
""",

    "socials": """
Generate 3 engaging social media posts summarizing the key message. Use:
- Hooks or headlines
- One or two key points
- Hashtags and emojis (if appropriate)

Make each post platform-ready for LinkedIn, Twitter, or Instagram.
""",

    "patient_leaf_lets": """
Write a patient-friendly leaflet based on the content. Include:
1. What it is about
2. How it helps the patient
3. What the patient should do or expect
4. Safety or usage guidance

Use warm, clear language and a supportive tone.
""",

    "video_scripts": """
Create a 60-second video script based on the document. Include:
1. Attention-grabbing intro
2. Clear explanation of the key idea
3. Summary or call to action

Use friendly, voiceover-suitable language.
"""
}




