from collections import defaultdict
import re
import numpy as np
import pandas as pd
from nltk.tokenize import word_tokenize
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.dom import minidom


"""
INPUTS:
    - conll from UDPipe (in a tab separated file)
    - minimal metadata provided by the user (title of the text, sentence IDs of the chapter titles):
        prendere queste info dalla fase di caricamento testo + inserimento titoli
    - (optional) concepts provided by the user
    
OUTPUTS:
    - txt file containing the text with xml tags
    - js file containing variables for the conll, the sentence list, the mappings concept_to_tok and tok_to_concept
"""

### RECEIVE INPUTS



### DEFINE FUNCTIONS:
    # 1) build_sent_list
    # 2) detect_concepts
    # 3) generate_tagged_text


# 1) FUNCTION FOR BUILDING A LIST WITH SENTENCE AND THEIR INFO

def build_sent_list(conll_df, titles_id):
    """
    PARAMETERS:
    conll_df: a pandas DataFrame containing the conll
    
    RETURN:
    sent_list: a list of dictionaries
    """
    
    sent_list = []

    for s in conll_df["sentence_id"].unique().tolist():    
        sent_list.append({"sent_id": s, 
                          "text": conll_df[conll_df["sentence_id"]==s].iloc[0]["sentence"], 
                          "type": "chapter title" if s in titles_id else "normal sentence"})
        
    return sent_list



# 2) FUNCTION FOR ADDING IOB TAGS AND MARKING CONCEPTS IN THE CONLL DATAFRAME

def detect_concepts(conll_df, concepts, reduce_processing=False, verbose=False):
    """
    Process the conll and add IOB tags to the tokens that represent an occurrence of a concept.

    PARAMETERS:
    1) conll_df: a pandas DataFrame containing the conll
    2) concepts: a list containing concepts
    3) reduce_processing (default False): if True, some token will not be processed because, 
                            considering its POS tag, there are low chances that this token 
                            can be the first token of a concept
                            (e.g. relative pronouns, conjunctions, punctuation, etc.).
                            However, in certain domains concept can start with such words,
                            so False is a safest option. 
    4) verbose: if True, the report of the processing will be printed (default False)

    RETURN:
    1) tagged_conll: a copy of the original pandas DataFrame containing two additional columns: 
                    - "iob", reporting "B", "I" or "_" (instead of "O")
                    - "part_of_concepts", containing the ID of the concept or "_" if it's not part of a concept
    2) tok_to_concept: a dictionary mapping the IDs of the tokens belonging to a concept with that concept
    3) concept_to_tok: a dictionary mapping every concept to the IDs of all its first tokens
    """
        
    def _is_candidate(token_row):
        """
        Helper function that deternines whether a token can be the first token of a concepts according to its POS.
        Return False (i.e. the token will be excluded from the processing) if the token has one of the following:
        
        punctuation
        DT
        EX (there)
        WD (relative pronouns)
        PR (personal pronouns)
        CC (conjunctions)
        RB (adverbs)
        WR (where, how, whereby)
        WP (what, who, whose)
        MD (modals)
        TO (to)
        """
        
        # TODO: check the tagset used by the conll
        
        if not reduce_processing:
            return True
        else:
            if token_row['xpos'] in [",", ".", "(", ";", ":", "'", ")", "?", "!", "EX", "WD", "PR", "WR", "WP", "CD", "MD", "CC", "RB", "TO"]:
                return False
            elif token_row['xpos'] in ["IN"] and token_row["lemma"].upper() not in ["WITH", "OF", "FOR", "OVER"]:
                return False
            # CD (numerals)
            elif token_row['xpos'] in ["DT"]:
                return False
            elif token_row['xpos'] in ['VBZ', 'VBP']:
                return False
            elif token_row['lemma'].upper() in ["HAVE", "BE", "ALL"]:
                return False
            else:
                return True
            
            
    tagged_conll = conll_df.copy()

    tagged_conll["iob"] = "_"
    tagged_conll["part_of_concept"] = "_"

    # initialize mappings

    # tokens IDs recognized as part of a concept
    tok_to_concept = {}
    # occurrences of the concepts across the text
    concept_to_tok = defaultdict(list)
    for c in concepts:
        concept_to_tok[c] = []

    concepts_not_recognized = concepts.copy()


    for tok_idx, tok_info in tagged_conll.iterrows():  

        if verbose:
            print("PROCESSING SENTENCE NUM:", tok_info["sentence_id"])
            print("\tProcessing token", tok_idx, "(number in sentence:", tok_info["token_id"], "):", tok_info["lemma"])
            print()

        # don't consider tokens already processed
            # (otherwise NETWORK in LOCAL AREA NETWORK will be tagged as a singleword concept with a "B" tag)

        #if _is_candidate(tok_info) and tok["iob_concept"] == "_":
        if _is_candidate(tok_info) and tok_idx not in tok_to_concept:

            results = []

            # find a first match with the first word of each concept
            for c in concepts:        
                # TODO: use the same tokenizer of the conll generator (i.e. UDPIPE)
                if word_tokenize(c)[0].upper() == tok_info["lemma"].upper():
                    if verbose:
                        print("\t\tCandidate match:", c)
                    results.append(c)

            if len(results) == 0:
                if verbose:
                    print("\t\tNo matching.")
            else:
                # keep track of the beginning and end of the concept
                start_tok = tok_idx 
                end_tok = tok_idx
                # save current lemma
                final_result = tok_info['lemma'].upper()
                # start from the longest concepts (to capture the longest match possible)
                results.sort(key = lambda s: len(s), reverse=True)

                if verbose:
                    print("\n\t\tProcessing all the candidate results:\n")

                # IDs of the tokens that are currently part of the concept
                curr_inside_tok_idx = []
                found = False

                for res in results:
                    if not found:
                        # start to match the next token with the next word of each candidate concept
                        next_concept_word = 1
                        next_tok_idx = tok_idx + 1 #int(tok_info["token_id"])

                        # stop searching a match when there are no tokens or words left and if the next token is a stopword
                        while (next_tok_idx in tagged_conll.index and 
                               next_concept_word < len(word_tokenize(res))):


                            next_tok_info = tagged_conll.loc[next_tok_idx]
                            
                            if verbose:
                                print("\t\t\tLooking for a match with:", res)
                                print("\t\t\t\tComparing token num", next_tok_info["token_id"], "(", next_tok_info["lemma"].upper(), ")", "with", word_tokenize(res)[next_concept_word])

                            if next_tok_info["lemma"].upper() == word_tokenize(res)[next_concept_word].upper():
                                
                                final_result += (" " + next_tok_info["lemma"].upper())
                                
                                if verbose:
                                    print("\t\t\t\t\tThere is a match...\n")
                                    print("\t\t\t\t\tMatching so far:", final_result)

                                    curr_inside_tok_idx.append(next_tok_idx)
                                # update the end of the concept
                                end_tok = end_tok + 1
                                # if the cursor on the concept words has reached the last word, set a flag
                                if next_concept_word == (len(word_tokenize(res))-1):
                                    
                                    if verbose:
                                        print("\t\t\t\t\tThe last word of a concept has been reached")
                                    
                                    found = True
                            else:
                                if verbose:
                                    print("\t\t\t\t\tNo matching.\n")
                                # reset the variables
                                curr_inside_tok_idx = []
                                end_tok = tok_idx #####+ 1 
                                # delete all the words previously inserted while looking for a match (except the first)
                                final_result = str(final_result.split()[0])
                                #pass

                            # slide forward both the cursors
                            next_concept_word +=1
                            next_tok_idx +=1


                if final_result.lower() in concepts:
                    final_result = final_result.lower()
                    
                    if verbose:
                        print("\t\t\t\tFinal result:", final_result)

                    if final_result.lower() in concepts_not_recognized:
                        concepts_not_recognized.remove(final_result)

                    concept_id =  concepts.index(final_result)
                    
                    # for the first token (B)
                    tagged_conll.at[start_tok,"iob"] = "B"
                    tagged_conll.at[start_tok,"part_of_concept"] = "autoconcept_" + str(concept_id)
                    # update info about the concept in the mappings
                    tok_to_concept[start_tok] = final_result
                    concept_to_tok[final_result].append(start_tok)
                    
                    # for all the other tokens (I)
                    for inside_tok in range(start_tok+1, end_tok+1):
                        tagged_conll.at[inside_tok,"iob"] = "I"
                        tagged_conll.at[inside_tok,"part_of_concept"] = "autoconcept_" + str(concept_id)
                        tok_to_concept[inside_tok] = final_result
                    if verbose:
                        print()

                else:
                    if verbose:
                        print("\n\t\t\t\tNo matching. Residual:", final_result)

            if verbose:
                print()
            
    return tagged_conll, tok_to_concept, concept_to_tok




# 3) FUNCTION FOR GENERATING ThE TEXT WITH XML TAGS

def generate_tagged_text(sent_list, conll_df, text_title, tok_to_concept, concept_to_tok, concepts, verbose=False):
    """
    PARAMETERS:
    1) sent_list:
    2) conll_df: a pandas DataFrame containing the conll, with or without "iob" and "part_of_concept" columns
    3) verbose: if True, the report of the processing will be printed (default False)
    
    RETURN:
    tagged_text: a text with annotated sentences, tokens and concepts, encoded in xml style tags
    
    
    TODO (eventually). 
    1) Modify the function to receive only one input (conll_df)
    2) Fix these minor issues to improve readability:
        - add whitespace after , and ;
        - delete whitespace after (
        - delete whitespaces before . and ,    
    """
    
    # TODO: 
    
    
    # add empty columns for concept tagging if they are not present
    for col in ["iob", "part_of_concept"]:
        if col not in conll_df.columns:
            conll_df[col] = "_"

    # initialize the xml tree
    root = Element('xml')
    root.set('version', '1.0')
    root.append(Comment(text_title))

    # nest everything inside <chapter></chapter>
    chapter_node = SubElement(root, "chapter")

    sent_node = SubElement(chapter_node, 'chapterTitle')

    # iterate through the list of sentences
    for s in sent_list:
        sent_id = s["sent_id"]
        sent_type = s["type"]

        # add a special node if it's a title

        if sent_type == "chapter title":
            sent_node = SubElement(chapter_node, 'chapterTitle')
        elif sent_type == "section title":
            # add double space before
            SubElement(chapter_node, 'br')
            SubElement(chapter_node, 'br')
            sent_node = SubElement(chapter_node, "sectionTitle")
        elif sent_type == "subsection title":
            # add double space before
            SubElement(chapter_node, 'br')
            SubElement(chapter_node, 'br')
            sent_node = SubElement(chapter_node, "subsectionTitle")
        else:
            # normal sentence: add single space before
            #if "sent_node" in globals(): # to handle the very first token
            sent_node.tail = " "
            sent_node = SubElement(chapter_node, "sent")

        sent_node.set("sent_id", str(sent_id))


        # iterate over the tokens in the current sentence  
            # NOTE: global_tok is the unique ID of each token (i.e. the ID of its row in the conll), 
                # curr_num_tok is the ID of each token in its sentence (i.e. its position in the sent, 
                    # i.e. the column token_id in the conll)
        for global_tok_id in conll_df[conll_df["sentence_id"] == sent_id].index:
            curr_tok = conll_df.loc[global_tok_id]
            curr_iob = conll_df.loc[global_tok_id]["iob"]
            curr_num_tok = conll_df.loc[global_tok_id]["token_id"]
            curr_concept_id = conll_df.loc[int(global_tok_id)]["part_of_concept"].replace("autoconcept_", "")
            try:
                prev_tok = conll_df.loc[int(global_tok_id)-1]["lemma"]
                prev_iob = conll_df.loc[int(global_tok_id)-1]["iob"]
                #prev_concept_id = str(conll_df.loc[int(global_tok_id)-1]["part_of_concept"])
                prev_concept_id = conll_df.loc[int(global_tok_id)-1]["part_of_concept"].replace("autoconcept_", "")
            except KeyError:
                prev_tok = ""
                prev_iob = "_"
                prev_concept = ""
                
            if verbose:
                print("_____________________________________________\n")
                print("Processing token", global_tok_id, "(sent num", sent_id, ", tok num", curr_num_tok, "):\n")
                print("\tlemma", "\tiob")
                print("\t", curr_tok["lemma"], "\t", curr_iob, "\n")
                print("\tprevious tok:")
                print("\tlemma", "\tiob")
                print("\t", prev_tok, "\t", prev_iob, "\n")    

            if curr_iob == "_":
                tok_node = SubElement(sent_node, "token")
                # convert to string, otherwise it won't be parsed
                tok_node.set("tok_id", str(global_tok_id))
                tok_node.set("partof_sent", str(sent_id))
                tok_node.set("pos_in_sent", str(curr_num_tok))
                tok_node.text = curr_tok["token"]
                
                #print(prev_iob)

                if prev_iob[0] in ["B", "I"]:
                    # the final token of a concept has been reached:
                    # find the concept node and insert an attribute with ID 
                    # (it's the concept node with still empty ID)
                    
                    if verbose:
                        print()
                        print('\tthe final token of a concept has been reached (prev_iob = "B" or "I")')
                        print("\t\tID of the identified concept:", prev_concept_id)
                        print()
                        #print(str(tostring(root).decode("utf-8")).replace("<chapterTitle />", ""))
                        #print()
                    
                    for c_n in sent_node.findall("concept"):
                        if str(c_n.attrib["concept_id"]) == "": 
                            
                            if verbose:
                                print("\t\t\tadding concept id")
                            
                            c_n.set("concept_id", prev_concept_id)
                            # find token nodes included in the concept and insert a ref to the concept
                            for t_n in c_n.findall("token"):
                                if int(t_n.attrib["tok_id"]) in concept_to_tok[concepts[int(prev_concept_id)]]:
                                    t_n.set("partof_autoconcept", prev_concept_id)
                            #if curr_tok["token"] not in [",", ".", ";", ":", "'", ")", "?", "!", "'s"] and prev_tok != "(":
                            c_n.tail = " "


            if curr_iob.startswith("B"):
                if prev_iob == "_": 
                    
                    if verbose:
                        print('\tthe starting token of a concept has been found (prev_iob = "_"):')
                        #print("\t\tID of the concept identified:", prev_concept_id)
                        print()
                    
                    concept_node = SubElement(sent_node, "concept")
                    concept_node.set("class", "automatic_concept")
                    concept_node.set("concept_id", curr_concept_id)
                    tok_node = SubElement(concept_node, "token")   
                    # convert to string, otherwise it won't be parsed
                    tok_node.set("tok_id", str(global_tok_id))
                    tok_node.set("partof_sent", str(sent_id))
                    tok_node.set("pos_in_sent", str(curr_num_tok))
                    tok_node.set("partof_autoconcept", curr_concept_id)
                    
                    if verbose:
                        print("\tadded a concept node")
                        #print("\n", str(tostring(root).decode("utf-8")).replace("<chapterTitle />", ""), "\n")
                    
                    tok_node.text = curr_tok["token"]

                else:
                    # the final token of a concept has been reached:
                    # find the concept node and insert an attribute with ID 
                    # (it's the concept node with still empty ID)
                    
                    if verbose:
                        print('\tthe final token of a concept has been reached (curr_iob = "B" and prev_iob != "_")')
                        print("\t\tID of the identified concept:", prev_concept_id)
                        print()
                        #print(str(tostring(root).decode("utf-8")).replace("<chapterTitle />", ""))
                        #print()
                    
                    for c_n in sent_node.findall("concept"):
                        if str(c_n.attrib["concept_id"]) == "": 
                            c_n.set("concept_id", prev_concept_id)
                            # find token nodes included in the concept and insert a ref to the concept
                            for t_n in c_n.findall("token"):
                                if int(t_n.attrib["tok_id"]) in concept_to_tok[concepts[int(prev_concept_id)]]:
                                    t_n.set("partof_autoconcept", prev_concept_id)
                            #if curr_tok["token"] not in [",", ".", ";", ":", "'", ")", "?", "!", "'s"] and prev_tok != "(":
                            c_n.tail = " "


                    concept_node = SubElement(sent_node, "concept")
                    concept_node.set("class", "automatic_concept")
                    concept_node.set("concept_id", "")
                    tok_node = SubElement(concept_node, "token")        
                    # convert to string, otherwise it won't be parsed
                    tok_node.set("tok_id", str(global_tok_id))
                    tok_node.set("partof_sent", str(sent_id))
                    tok_node.set("pos_in_sent", str(curr_num_tok))
                    tok_node.text = curr_tok["token"]


            if curr_iob.startswith("I"):
                
                if verbose:
                    print()
                    print('\tan inside token of a concept has been found (curr_iob = "I")')
                    print()
                    
                tok_node = SubElement(concept_node, "token")
                # convert to string, otherwise it won't be parsed
                tok_node.set("tok_id", str(global_tok_id))
                tok_node.set("partof_sent", str(sent_id))
                tok_node.set("pos_in_sent", str(curr_num_tok))
                tok_node.set("partof_autoconcept", curr_concept_id)
                tok_node.text = curr_tok["token"]

            # add whitespace if needed
            #if curr_tok["token"] not in [",", ".", ";", ":", "'", ")", "?", "!", "'s"] and prev_tok != "(":
            tok_node.tail = " "


        # add double line breaks after titles
        if sent_type in ["chapter title", "section title", "subsection title"]:
            SubElement(chapter_node, 'br')
            SubElement(chapter_node, 'br')


     # delete a possible empty <chapterTitle />
    tagged_text = str(tostring(root).decode("utf-8")).replace("<chapterTitle />", "")
    # fix the undesired white spaces between </token> and </concept> closing tags
    pattern = r"</token> </concept><"
    new_pattern = r"</token></concept> <"
    tagged_text = re.sub(pattern, new_pattern, tagged_text) 
    
    
    return tagged_text




### OPEN CONLL AND CALL THE FUNCTIONS TO PROCESS IT
def conll_processor(conll, title, sentences, concepts):
    conll_df = pd.read_csv(pd.compat.StringIO(conll))
    tok_to_concept = []
    concept_to_tok = []
    text_title = title
    titles_id = sentences 
    sent_list = build_sent_list(conll_df, titles_id)
    tagged_conll, tok_to_concept, concept_to_tok = detect_concepts(conll_df, concepts, reduce_processing=False, verbose=False)
    tagged_text = generate_tagged_text(sent_list, tagged_conll, text_title, tok_to_concept, concept_to_tok, concepts, verbose=False)
    return tagged_text, sent_list, tok_to_concept, concept_to_tok

### EXPORT RESULTS:

    # 1) tagged text

#with open('prova_testo_taggato.txt', 'w', encoding="utf-8-sig") as f:
#    f.write(tagged_text)
#    
#    # 2) list of sentences 
#    # 3) conll dataframe
#    # 4) mapping concept_to_tok
#    # 5) mapping tok_to_concep
    
#with open('prova_database_IIR.js', 'w', encoding="utf-8-sig") as f:
#    f.write("var $autoConcepts = ")
#    f.write(str(concepts))
#    f.write(";\n\n")
#    f.write("var $sentList = ")
#    f.write(str(sent_list))
#    f.write(";\n\n")
#    f.write("var $conll = ")
#    # convert nan values to empty strings for compatibility with javascript
#    tagged_conll = tagged_conll.replace(np.nan, '', regex=True)
#    f.write(str(tagged_conll.reset_index().to_dict(orient="records")))
#    f.write(";\n\n")
#    f.write("var $conceptToTok = ")
#    # convert defaultdict to simple dictionary for compatibility with javascript
#    f.write(str(dict(concept_to_tok))) 
#    f.write(";\n\n")
#    f.write("var $tokToConcept = ")
#    f.write(str(tok_to_concept))
#    f.write(";\n")