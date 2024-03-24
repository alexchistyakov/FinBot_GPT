# A simple class for building JSON schemas for AI and converting them into appropriate grammar rules
import json
from jsonschemaconverter import SchemaConverter
from genson import SchemaBuilder

builder = SchemaBuilder()

builder.add_schema({
        "type": "object",
        "propterties": {}
    })

# ========== SCHEMA BUILD CODE =============
builder.add_object({"extracted_info_about_ticker": "str"})
builder.add_object({"contains_info_on_ticker": False})
builder.add_object({"ticker": "str"})
#builder.add_object({"date_start":"str"})
#builder.add_object({"date_end":"str"})
# ==========================================

schema = builder.to_schema()

def generate_grammar(schema):
    converter = SchemaConverter({})
    converter.visit(schema, '')
    return converter.format_grammar()

print(generate_grammar(schema))
dictionary = {"grammar" : generate_grammar(schema)}
with open("generated_grammar.json", "w") as outfile:
    outfile.write(json.dumps(dictionary))
