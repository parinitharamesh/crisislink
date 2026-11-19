"""
ChromaDB Vector Search Routes
Semantic search over disaster knowledge using sentence-transformers.
Unit 4: Vector Databases, Vector Search
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request
from config.chromadb_config import get_collection
from middleware.auth_middleware import role_required
import uuid

chroma_bp = Blueprint('chroma', __name__)

# ─── Disaster knowledge base documents ───────────────────────────────────────
KNOWLEDGE_BASE = [
    {
        'id': 'kb-flood-001',
        'text': 'Flood evacuation procedure: Move to higher ground immediately. '
                'Avoid walking in moving water. Never drive through flooded roads. '
                'Turn off utilities at main switches. Disconnect electrical appliances.',
        'metadata': {'category': 'flood', 'type': 'evacuation_guide', 'language': 'en'}
    },
    {
        'id': 'kb-flood-002',
        'text': 'Rescue boat deployment in flood zones: Prioritize stranded individuals '
                'on rooftops and upper floors. Use life jackets. Rescue teams should '
                'work in pairs. Maintain communication with coordination center.',
        'metadata': {'category': 'flood', 'type': 'rescue_procedure', 'language': 'en'}
    },
    {
        'id': 'kb-medical-001',
        'text': 'Emergency medical supplies checklist for disaster response: '
                'Bandages, antiseptic, paracetamol, oral rehydration salts, '
                'insulin kits for diabetics, blood pressure medication, '
                'trauma kits, stretchers, oxygen cylinders.',
        'metadata': {'category': 'medical', 'type': 'supplies_checklist', 'language': 'en'}
    },
    {
        'id': 'kb-medical-002',
        'text': 'Medical triage during mass casualty events: Sort patients by severity. '
                'RED = immediate life threat. YELLOW = delayed treatment possible. '
                'GREEN = walking wounded. BLACK = deceased or unsurvivable.',
        'metadata': {'category': 'medical', 'type': 'triage_guide', 'language': 'en'}
    },
    {
        'id': 'kb-cyclone-001',
        'text': 'Cyclone preparedness and response: Evacuate coastal areas before landfall. '
                'Stock food and water for 3-7 days. Identify nearest cyclone shelter. '
                'Secure loose objects. Stay indoors during cyclone. Do not go out in eye calm.',
        'metadata': {'category': 'cyclone', 'type': 'preparedness_guide', 'language': 'en'}
    },
    {
        'id': 'kb-shelter-001',
        'text': 'Emergency shelter management: Maintain 3.5 square meters per person. '
                'Separate sections for families, women, medical cases. '
                'Ensure sanitation facilities ratio 1:20. Register all occupants.',
        'metadata': {'category': 'shelter', 'type': 'management_guide', 'language': 'en'}
    },
    {
        'id': 'kb-food-001',
        'text': 'Emergency food distribution: Provide minimum 2100 kcal per person per day. '
                'Focus on ready-to-eat non-perishable items. Prioritize children, pregnant '
                'women, elderly. Use systematic registration to prevent duplication.',
        'metadata': {'category': 'food', 'type': 'distribution_guide', 'language': 'en'}
    },
    {
        'id': 'kb-water-001',
        'text': 'Emergency water supply during disaster: Minimum 15 litres per person per day. '
                'Use water purification tablets. Boil water before drinking. '
                'Test water quality before distribution. Tanker trucks can supply 5000L.',
        'metadata': {'category': 'water', 'type': 'supply_guide', 'language': 'en'}
    },
    {
        'id': 'kb-earthquake-001',
        'text': 'Earthquake response: Drop, cover, hold during shaking. '
                'After shaking stops, check for injuries. Evacuate damaged buildings. '
                'Beware of aftershocks. Use heavy machinery for debris removal. '
                'Search for trapped survivors in first 72 hours is critical.',
        'metadata': {'category': 'earthquake', 'type': 'response_guide', 'language': 'en'}
    },
    {
        'id': 'kb-landslide-001',
        'text': 'Landslide rescue operations: Use heavy excavators and cranes for debris removal. '
                'Search dogs can locate trapped victims. Do not enter unstable slopes. '
                'Set up exclusion zones. Monitor for secondary landslides after rain.',
        'metadata': {'category': 'landslide', 'type': 'rescue_guide', 'language': 'en'}
    },
    {
        'id': 'kb-coordination-001',
        'text': 'Disaster response coordination: Establish unified command center. '
                'Use satellite communication for areas with no mobile network. '
                'Coordinate with NDRF, Army, Police and NGOs. Track all resources '
                'and assignments to prevent duplication and gaps in coverage.',
        'metadata': {'category': 'coordination', 'type': 'operations_guide', 'language': 'en'}
    },
    {
        'id': 'kb-trapped-001',
        'text': 'Protocol for people trapped in buildings during floods or earthquakes: '
                'Signal rescuers by waving bright cloth or using whistle. '
                'Conserve energy and stay calm. Stay above water level. '
                'Do not use elevators. Move to roof if water rises.',
        'metadata': {'category': 'survival', 'type': 'survival_guide', 'language': 'en'}
    },
    {
        'id': 'kb-chemical-001',
        'text': 'Industrial chemical leak response: Immediate evacuation of 1km radius. '
                'Use N95 or gas masks if available. Do not enter affected zone without PPE. '
                'Neutralize spill with appropriate agents. Decontaminate exposed persons.',
        'metadata': {'category': 'industrial', 'type': 'hazmat_guide', 'language': 'en'}
    },
    {
        'id': 'kb-volunteer-001',
        'text': 'Managing disaster response volunteers: Register all volunteers. '
                'Match skills to tasks (medical, logistics, search and rescue). '
                'Provide briefing on safety procedures. Ensure they have proper equipment.',
        'metadata': {'category': 'coordination', 'type': 'volunteer_guide', 'language': 'en'}
    },
    {
        'id': 'kb-communication-001',
        'text': 'Emergency communication during disasters: Establish radio communication. '
                'Use satellite phones when mobile networks fail. Set up repeater stations. '
                'Assign frequencies to each response team. Use standardized codes.',
        'metadata': {'category': 'communication', 'type': 'comms_guide', 'language': 'en'}
    }
]


@chroma_bp.route('/init', methods=['POST'])
@role_required('ADMIN')
def init_knowledge_base():
    """Initialize ChromaDB with disaster knowledge documents."""
    try:
        collection = get_collection()

        # Clear and reload
        existing = collection.count()
        if existing > 0:
            collection.delete(ids=[doc['id'] for doc in KNOWLEDGE_BASE
                                   if collection.get(ids=[doc['id']])['ids']])

        collection.upsert(
            ids=[doc['id'] for doc in KNOWLEDGE_BASE],
            documents=[doc['text'] for doc in KNOWLEDGE_BASE],
            metadatas=[doc['metadata'] for doc in KNOWLEDGE_BASE]
        )

        return jsonify({
            'message': f'Knowledge base initialized with {len(KNOWLEDGE_BASE)} documents',
            'count': collection.count()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chroma_bp.route('/search', methods=['GET'])
def semantic_search():
    """
    Semantic similarity search using vector embeddings.
    Example queries:
    - "flood evacuation procedure"
    - "medical supplies for disaster"
    - "people trapped during heavy rainfall"
    """
    try:
        verify_jwt_in_request()
        query = request.args.get('q', '').strip()
        n     = min(int(request.args.get('n', 5)), 10)
        category = request.args.get('category')

        if not query:
            return jsonify({'error': 'Query parameter "q" is required'}), 400

        collection = get_collection()

        # Build metadata filter if category specified
        where = {'category': category} if category else None

        results = collection.query(
            query_texts=[query],
            n_results=n,
            where=where,
            include=['documents', 'metadatas', 'distances']
        )

        # Format results
        hits = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                hits.append({
                    'id':       doc_id,
                    'text':     results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'similarity': round(1 - results['distances'][0][i], 4)
                })

        return jsonify({
            'query':   query,
            'results': hits,
            'count':   len(hits)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chroma_bp.route('/documents', methods=['POST'])
@role_required('ADMIN', 'COORDINATOR')
def add_document():
    """Add a new document to the knowledge base."""
    data = request.get_json()
    if not data.get('text'):
        return jsonify({'error': 'text is required'}), 400

    try:
        collection = get_collection()
        doc_id = data.get('id', str(uuid.uuid4()))

        collection.upsert(
            ids=[doc_id],
            documents=[data['text']],
            metadatas=[data.get('metadata', {})]
        )

        return jsonify({'message': 'Document added', 'id': doc_id, 'count': collection.count()}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chroma_bp.route('/documents/<doc_id>', methods=['DELETE'])
@role_required('ADMIN')
def delete_document(doc_id):
    """Delete a document from the knowledge base."""
    try:
        collection = get_collection()
        collection.delete(ids=[doc_id])
        return jsonify({'message': 'Document deleted', 'remaining': collection.count()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chroma_bp.route('/stats', methods=['GET'])
def chroma_stats():
    """Get knowledge base statistics."""
    try:
        verify_jwt_in_request()
        collection = get_collection()
        count = collection.count()

        # Get all documents to show category breakdown
        all_docs = collection.get(include=['metadatas'])
        categories = {}
        for meta in (all_docs.get('metadatas') or []):
            cat = meta.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1

        return jsonify({
            'total_documents': count,
            'categories': categories,
            'collection_name': 'crisis_knowledge',
            'embedding_model': 'all-MiniLM-L6-v2'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
