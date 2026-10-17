# Knowledge base: rules and questions

Generated from `app.py`. Each rule is `IF all conditions hold THEN conclude an urgency level`. All rules whose conditions hold fire (forward chaining); the **highest urgency wins**.

## Urgency levels

| Level | Label | Meaning |
|---:|---|---|
| 4 | Emergency | Call your local emergency number now. |
| 3 | Urgent | Get medical care today. |
| 2 | See a doctor soon | Book an appointment within 1–3 days. |
| 1 | Self-care at home | You can probably look after this at home. |

## Questions (in the order they can be asked)

| Id | Question | Type | Asked when | Used by rules |
|---|---|---|---|---|
| `redflags` | Right now, do you have any of these? | multi | always | 9 |
| `age` | How old is the person who needs advice? | single | always | 20 |
| `complaint` | What is the main problem? | single | always | 58 |
| `risk` | Does any of this apply? A long-term illness (heart, lung, kidney, diabetes), a weakened immune system (for example chemotherapy, steroids or a transplant), or pregnancy. | single | always | 5 |
| `temp` | What is the highest temperature so far? | single | main problem = fever | 8 |
| `fever_days` | How long has the fever lasted? | single | main problem = fever | 1 |
| `fever_sx` | Any of these with the fever? | multi | main problem = fever | 6 |
| `cough_breath` | How is your breathing? | single | main problem = cough | 3 |
| `cough_days` | How long have you had the cough? | single | main problem = cough | 2 |
| `cough_sx` | Any of these? | multi | main problem = cough | 6 |
| `throat_sx` | Any of these? | multi | main problem = throat | 5 |
| `throat_days` | How long has the sore throat lasted? | single | main problem = throat | 1 |
| `ha_onset` | How did the headache start? | single | main problem = headache | 1 |
| `ha_sx` | Any of these? | multi | main problem = headache | 5 |
| `ha_known` | Have you had headaches like this before? | single | main problem = headache | 2 |
| `gi_sx` | Any of these? | multi | main problem = stomach | 5 |
| `gi_fluids` | Can you keep fluids down? | single | main problem = stomach | 3 |
| `gi_days` | How long have the symptoms lasted? | single | main problem = stomach | 2 |

## Rules

| Rule | Level | IF | THEN |
|---|---|---|---|
| RF1 | 4 Emergency | Danger signs includes: “Severe trouble breathing, or can't speak a full sentence” (any) | Severe trouble breathing can become life-threatening quickly. |
| RF2 | 4 Emergency | Danger signs includes: “Chest pain, pressure or tightness” (any) | Chest pain, pressure or tightness can be a sign of a heart problem and needs emergency assessment. |
| RF3 | 4 Emergency | Danger signs includes: “Blue or grey lips or face” (any) | Blue or grey lips or face can mean the body is not getting enough oxygen. |
| RF4 | 4 Emergency | Danger signs includes: “Fainted, can't be woken, or sudden confusion” (any) | Fainting, being unable to wake, or sudden confusion needs emergency help. |
| RF5 | 4 Emergency | Danger signs includes: “Sudden face drooping, arm or leg weakness, or slurred speech” (any) | Sudden face drooping, limb weakness or slurred speech can be signs of a stroke. Minutes matter. |
| RF6 | 4 Emergency | Danger signs includes: “Heavy bleeding that won't stop with firm pressure” (any) | Heavy bleeding that will not stop with firm pressure needs emergency help. |
| RF7 | 4 Emergency | Danger signs includes: “A seizure (fit) now or just now” (any) | A seizure needs emergency assessment, especially a first one or one lasting over 5 minutes. |
| RF8 | 4 Emergency | Danger signs includes: “Swelling of lips, face or tongue, or throat tightness after a sting, food or medicine” (any) | Swelling of the lips, face or tongue, or throat tightness, can be a severe allergic reaction. |
| RF9 | 4 Emergency | Danger signs includes: “Thoughts of harming yourself or someone else” (any) | You may be at risk of harm. Please contact emergency services or a crisis line now; you do not have to face this alone. |
| F1 | 4 Emergency | Main problem is “Fever, or feeling feverish” AND Age group is “Under 3 months” AND Highest temperature is one of: “38 to 38.9 °C (100.4 to 102 °F)”; “39 to 39.9 °C (102.1 to 103.8 °F)”; “40 °C (104 °F) or higher”; “Not measured, but feels hot” | A fever of 38 °C or more in a baby under 3 months needs an emergency assessment, even if the baby looks well. |
| F2 | 3 Urgent | Main problem is “Fever, or feeling feverish” AND Age group is “Under 3 months” | Any sign of fever in a baby under 3 months should be checked by a clinician today. |
| F3 | 3 Urgent | Main problem is “Fever, or feeling feverish” AND Age group is “3 to 11 months” AND Highest temperature is one of: “39 to 39.9 °C (102.1 to 103.8 °F)”; “40 °C (104 °F) or higher”; “Not measured, but feels hot” | A high or unmeasured fever in a baby aged 3 to 11 months should be checked today. |
| F4 | 2 See a doctor soon | Main problem is “Fever, or feeling feverish” AND Age group is “3 to 11 months” AND Highest temperature is “38 to 38.9 °C (100.4 to 102 °F)” | A fever in a baby aged 3 to 11 months should be checked by a doctor soon. |
| F5 | 4 Emergency | Main problem is “Fever, or feeling feverish” AND Fever warning signs includes: “Stiff neck, or pain when looking at bright light”; “A rash that does not fade when a glass is pressed on it” (any) | A stiff neck, light sensitivity or a rash that does not fade, together with fever, can be signs of a serious infection that needs emergency care. |
| F6 | 4 Emergency | Main problem is “Fever, or feeling feverish” AND Age group is one of: “Under 3 months”; “3 to 11 months”; “1 to 12 years” AND Fever warning signs includes: “Very drowsy, floppy or hard to wake” (any) | A feverish child or baby who is very drowsy, floppy or hard to wake needs emergency care. |
| F7 | 3 Urgent | Main problem is “Fever, or feeling feverish” AND Age group is one of: “13 to 64 years”; “65 or older” AND Fever warning signs includes: “Very drowsy, floppy or hard to wake” (any) | Being very drowsy with a fever should be assessed by a clinician today. |
| F8 | 3 Urgent | Main problem is “Fever, or feeling feverish” AND Highest temperature is “40 °C (104 °F) or higher” | A temperature of 40 °C or higher should be assessed today. |
| F9 | 3 Urgent | Main problem is “Fever, or feeling feverish” AND Fever warning signs includes: “Repeated vomiting, can't keep fluids down” (any) AND Age group is one of: “Under 3 months”; “3 to 11 months”; “1 to 12 years”; “65 or older” | Repeated vomiting with a fever risks dehydration, which is more dangerous in the very young and the elderly. |
| F10 | 2 See a doctor soon | Main problem is “Fever, or feeling feverish” AND Fever warning signs includes: “Repeated vomiting, can't keep fluids down” (any) AND Age group is “13 to 64 years” | Repeated vomiting with a fever can lead to dehydration and should be checked soon. |
| F11 | 3 Urgent | Main problem is “Fever, or feeling feverish” AND Higher-risk condition is “Yes” AND Highest temperature is one of: “38 to 38.9 °C (100.4 to 102 °F)”; “39 to 39.9 °C (102.1 to 103.8 °F)”; “40 °C (104 °F) or higher”; “Not measured, but feels hot” | A fever with a long-term illness, a weakened immune system or pregnancy should be assessed today. |
| F12 | 3 Urgent | Main problem is “Fever, or feeling feverish” AND Age group is “65 or older” AND Highest temperature is one of: “39 to 39.9 °C (102.1 to 103.8 °F)”; “40 °C (104 °F) or higher” | A high fever in someone aged 65 or older should be assessed today. |
| F13 | 2 See a doctor soon | Main problem is “Fever, or feeling feverish” AND Age group is “65 or older” AND Highest temperature is “38 to 38.9 °C (100.4 to 102 °F)” | A fever in someone aged 65 or older should be checked soon. |
| F14 | 2 See a doctor soon | Main problem is “Fever, or feeling feverish” AND Age group is “1 to 12 years” AND Highest temperature is one of: “39 to 39.9 °C (102.1 to 103.8 °F)”; “40 °C (104 °F) or higher” | A high fever in a child should be checked by a doctor soon if it does not settle. |
| F15 | 2 See a doctor soon | Main problem is “Fever, or feeling feverish” AND Fever length is “More than 3 days” | A fever lasting more than 3 days should be checked. |
| F16 | 2 See a doctor soon | Main problem is “Fever, or feeling feverish” AND Fever warning signs includes: “Pain or burning when passing urine” (any) | Pain or burning when passing urine with a fever can mean an infection that needs treatment. |
| F0 | 1 Self-care at home | Main problem is “Fever, or feeling feverish” | Fever on its own is common with infections and often settles with rest and fluids. |
| C1 | 3 Urgent | Main problem is “Cough or a breathing problem” AND Breathing is “Short of breath even at rest or while talking” | Being short of breath at rest or while talking should be assessed today. |
| C2 | 3 Urgent | Main problem is “Cough or a breathing problem” AND Cough warning signs includes: “Coughing up blood” (any) | Coughing up blood should be assessed today. |
| C3 | 3 Urgent | Main problem is “Cough or a breathing problem” AND Age group is one of: “Under 3 months”; “3 to 11 months”; “1 to 12 years” AND Cough warning signs includes: “Wheezing or a whistling sound when breathing” (any) | Wheezing in a baby or child should be assessed today. |
| C4 | 2 See a doctor soon | Main problem is “Cough or a breathing problem” AND Age group is one of: “13 to 64 years”; “65 or older” AND Cough warning signs includes: “Wheezing or a whistling sound when breathing” (any) | Wheezing should be checked by a doctor soon. |
| C5 | 3 Urgent | Main problem is “Cough or a breathing problem” AND Age group is “Under 3 months” | A cough in a baby under 3 months should be checked today. |
| C6 | 3 Urgent | Main problem is “Cough or a breathing problem” AND Age group is “3 to 11 months” AND Breathing is one of: “A bit short of breath when active or climbing stairs”; “Short of breath even at rest or while talking” | Breathing difficulty with a cough in a baby should be checked today. |
| C7 | 2 See a doctor soon | Main problem is “Cough or a breathing problem” AND Breathing is “A bit short of breath when active or climbing stairs” | Being short of breath when active should be checked soon. |
| C8 | 2 See a doctor soon | Main problem is “Cough or a breathing problem” AND Cough length is “More than 3 weeks” | A cough lasting more than 3 weeks should be checked. |
| C9 | 3 Urgent | Main problem is “Cough or a breathing problem” AND Higher-risk condition is “Yes” AND Cough warning signs includes: “Fever of 38 °C (100.4 °F) or higher” (any) | A cough with fever and a long-term illness, weakened immune system or pregnancy should be assessed today. |
| C10 | 2 See a doctor soon | Main problem is “Cough or a breathing problem” AND Cough warning signs includes: “Chest pain when breathing in or coughing” (any) | Chest pain when breathing or coughing should be checked soon. |
| C11 | 2 See a doctor soon | Main problem is “Cough or a breathing problem” AND Cough warning signs includes: “Fever of 38 °C (100.4 °F) or higher” (any) AND Cough length is one of: “1 to 3 weeks”; “More than 3 weeks” | A cough with fever lasting over a week should be checked. |
| C0 | 1 Self-care at home | Main problem is “Cough or a breathing problem” | Most coughs come from colds and clear up on their own within about 3 weeks. |
| S1 | 4 Emergency | Main problem is “Sore throat or cold” AND Throat warning signs includes: “Can't swallow your own saliva, or drooling” (any) | Being unable to swallow saliva, or drooling, can mean the airway is at risk and needs emergency care. |
| S2 | 3 Urgent | Main problem is “Sore throat or cold” AND Throat warning signs includes: “Muffled voice, or can't open your mouth fully” (any) | A muffled voice or being unable to open the mouth fully should be assessed today. |
| S3 | 3 Urgent | Main problem is “Sore throat or cold” AND Higher-risk condition is “Yes” AND Throat warning signs includes: “High fever (38.5 °C / 101.3 °F or more) and no cough” (any) | A high fever with a sore throat and a higher-risk condition should be assessed today. |
| S4 | 2 See a doctor soon | Main problem is “Sore throat or cold” AND Throat warning signs includes: “High fever (38.5 °C / 101.3 °F or more) and no cough” (any) | A high fever with a sore throat and no cough should be checked soon. |
| S5 | 2 See a doctor soon | Main problem is “Sore throat or cold” AND Throat warning signs includes: “White patches or pus on the tonsils” (any) | White patches or pus on the tonsils should be checked soon. |
| S6 | 2 See a doctor soon | Main problem is “Sore throat or cold” AND Throat length is “A week or more” | A sore throat lasting a week or more should be checked. |
| S0 | 1 Self-care at home | Main problem is “Sore throat or cold” | Most sore throats come from colds and settle within a week. |
| H1 | 4 Emergency | Main problem is “Headache” AND Headache start is “Suddenly: the worst headache of my life, peaking within a minute” | A sudden, severe 'worst ever' headache needs emergency assessment. |
| H2 | 4 Emergency | Main problem is “Headache” AND Headache warning signs includes: “Fever and a stiff neck” (any) | A headache with fever and a stiff neck can be a sign of a serious infection and needs emergency care. |
| H3 | 3 Urgent | Main problem is “Headache” AND Headache warning signs includes: “It started after a blow to the head” (any) | A headache after a blow to the head should be assessed today. |
| H4 | 3 Urgent | Main problem is “Headache” AND Headache warning signs includes: “Vision changes: blurred, double or lost vision” (any) | A headache with vision changes should be assessed today. |
| H5 | 3 Urgent | Main problem is “Headache” AND Headache warning signs includes: “Repeated vomiting” (any) | A headache with repeated vomiting should be assessed today. |
| H6 | 2 See a doctor soon | Main problem is “Headache” AND Headache warning signs includes: “Pain getting steadily worse over days or weeks, or waking me at night” (any) | A headache that keeps getting worse, or wakes you at night, should be checked soon. |
| H7 | 2 See a doctor soon | Main problem is “Headache” AND Familiar headache is “No, this feels new or different” AND Age group is “65 or older” | A new kind of headache at 65 or older should be checked soon. |
| H8 | 2 See a doctor soon | Main problem is “Headache” AND Familiar headache is “No, this feels new or different” AND Higher-risk condition is “Yes” | A new kind of headache with a higher-risk condition should be checked soon. |
| H0 | 1 Self-care at home | Main problem is “Headache” | Most headaches are tension-type or migraine-type and ease with rest, fluids and pain relief. |
| G1 | 4 Emergency | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Stomach warning signs includes: “Vomiting blood, or black or bloody stools” (any) | Vomiting blood, or black or bloody stools, can mean serious bleeding and needs emergency care. |
| G2 | 4 Emergency | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Stomach warning signs includes: “A very swollen, hard or rigid belly” (any) | A very swollen, hard belly needs emergency assessment. |
| G3 | 3 Urgent | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Stomach warning signs includes: “Severe belly pain that is constant or getting worse” (any) | Severe belly pain that is constant or getting worse should be assessed today. |
| G4 | 3 Urgent | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Stomach warning signs includes: “Pain low on the right side of the belly, with fever” (any) | Pain low on the right side with fever should be assessed today. |
| G5 | 3 Urgent | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Stomach warning signs includes: “Dehydration: very dry mouth, little or no urine in 8 hours, dizzy when standing” (any) | Signs of dehydration should be assessed today. |
| G6 | 3 Urgent | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Keeping fluids down is “No, I vomit most fluids” AND Age group is one of: “Under 3 months”; “3 to 11 months”; “1 to 12 years”; “65 or older” | Not keeping fluids down risks dehydration, which is more dangerous in the very young and the elderly. |
| G7 | 3 Urgent | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Keeping fluids down is “No, I vomit most fluids” AND Higher-risk condition is “Yes” | Not keeping fluids down with a higher-risk condition should be assessed today. |
| G8 | 2 See a doctor soon | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Keeping fluids down is “No, I vomit most fluids” AND Age group is “13 to 64 years” | Not keeping fluids down should be checked soon. |
| G9 | 3 Urgent | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Age group is “Under 3 months” | Vomiting, diarrhea or belly pain in a baby under 3 months should be checked today. |
| G10 | 2 See a doctor soon | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Stomach length is “More than 7 days” | Stomach symptoms lasting more than a week should be checked. |
| G11 | 2 See a doctor soon | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” AND Stomach length is “2 to 7 days” AND Age group is one of: “3 to 11 months”; “1 to 12 years”; “65 or older” | Stomach symptoms lasting more than 2 days in a baby, child or older adult should be checked. |
| G0 | 1 Self-care at home | Main problem is “Stomach upset (vomiting, diarrhea, belly pain)” | Most stomach upsets pass within a couple of days with fluids and rest. |
| X1 | 2 See a doctor soon | Main problem is “Something else” | This checker only covers fever, cough, sore throat, headache and stomach upset. For anything else, talk to a doctor or nurse. |

Total: 67 rules, 18 questions.
