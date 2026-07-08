from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Load embedding model once
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Connect to existing ChromaDB
vectorstore = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings
)

# Create retriever
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 5}
)


def retrieve_docs(question: str):
    """
    Returns the top-k relevant documents for a given question.
    """
    return retriever.invoke(question)


def retrieve_context(question: str):
    """
    Returns a single context string for the LLM.
    """
    docs = retrieve_docs(question)

    context = "\n\n".join(
        doc.page_content for doc in docs
    )

    return docs, context


# -------------------------
# Test
if __name__ == "__main__":

    question = "What is Transcend Platform?"

    docs, context = retrieve_context(question)

    print(f"Retrieved {len(docs)} documents.\n")

    for i, doc in enumerate(docs, 1):
        print(f"--- Result {i} ---")
        print(doc.metadata)
        print(doc.page_content[:500])
        print()

"""Now, anywhere in your project you can simply do:

from retriever import retrieve_context
docs, context = retrieve_context("What is Transcend Platform?")"""