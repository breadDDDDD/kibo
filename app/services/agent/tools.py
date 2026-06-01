"""
Gemini tool declarations — FunctionDeclaration schemas passed to the model.
Two tools: RAG catalog search + DB stock lookup.
"""
import google.generativeai as genai

search_parts_catalog_tool = genai.protos.FunctionDeclaration(
    name="search_parts_catalog",
    description=(
        "Searches the Mitsubishi parts catalog PDFs using semantic similarity. "
        "Use this when the user describes a part by name, location, or function. "
        "Returns relevant catalog chunks containing part names, descriptions, and product numbers."
    ),
    parameters=genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties={
            "query": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description=(
                    "The search query — use the user's description as-is or refine it "
                    "to be more specific (e.g. 'bumper depan Xpander', 'oil filter Pajero Sport')."
                ),
            )
        },
        required=["query"],
    ),
)

get_stock_by_part_id_tool = genai.protos.FunctionDeclaration(
    name="get_stock_by_part_id",
    description=(
        "Looks up the current stock level for a specific part number in the warehouse database. "
        "Use ONLY after you have a confirmed alphanumeric product_number from the catalog."
    ),
    parameters=genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties={
            "product_number": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description=(
                    "The exact alphanumeric part/product number "
                    "(e.g. '7450A951', 'MD360935M'). Case-insensitive."
                ),
            ),
            "part_name": genai.protos.Schema(
                type=genai.protos.Type.STRING,
                description=(
                    "The human-readable part name extracted from the catalog chunk "
                    "(e.g. 'Front Bumper Assembly', 'Oil Filter Element'). "
                    "Extract this from the catalog context — do NOT invent it."
                ),
            ),
        },
        required=["product_number", "part_name"],
    ),
)

TOOLS = genai.protos.Tool(
    function_declarations=[
        search_parts_catalog_tool,
        get_stock_by_part_id_tool,
    ]
)