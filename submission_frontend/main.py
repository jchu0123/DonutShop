import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google.adk.sessions import VertexAiSessionService
import vertexai

app = FastAPI(title="Manager Dashboard")

# Read configuration from environment variables
PROJECT_ID = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
AGENT_RUNTIME_ID = os.environ.get("AGENT_RUNTIME_ID")
LOCATION = os.environ.get("LOCATION", "us-east1")

# Robust parser for AGENT_RUNTIME_ID
def parse_runtime_id(runtime_id: str | None, default_project: str | None, default_location: str):
    if not runtime_id:
        return default_project, default_location, None
    if runtime_id.startswith("projects/"):
        parts = runtime_id.split("/")
        return parts[1], parts[3], parts[5]
    return default_project, default_location, runtime_id

class ActionRequest(BaseModel):
    interrupt_id: str
    approved: bool

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Donut Shop - Manager Dashboard</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {
                --pink-primary: #ff6b8b;
                --pink-hover: #ff4770;
                --pink-light: #fff0f3;
                --chocolate: #4a2c2a;
                --yellow-gold: #ffb703;
                --success-green: #2ec4b6;
                --glass-bg: rgba(255, 255, 255, 0.7);
                --glass-border: rgba(255, 255, 255, 0.4);
                --text-dark: #2d2325;
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Outfit', sans-serif;
            }

            body {
                background: linear-gradient(135deg, #ffe5ec 0%, #ffc2d1 50%, #ffe5ec 100%);
                min-height: 100vh;
                color: var(--text-dark);
                position: relative;
                overflow-x: hidden;
            }

            /* Decorative radial glows */
            .glow-1 {
                position: absolute;
                width: 400px;
                height: 400px;
                background: radial-gradient(circle, rgba(255, 183, 3, 0.3) 0%, rgba(255,255,255,0) 70%);
                top: -100px;
                left: -100px;
                z-index: 0;
                pointer-events: none;
            }

            .glow-2 {
                position: absolute;
                width: 500px;
                height: 500px;
                background: radial-gradient(circle, rgba(255, 107, 139, 0.3) 0%, rgba(255,255,255,0) 70%);
                bottom: -150px;
                right: -100px;
                z-index: 0;
                pointer-events: none;
            }

            header {
                backdrop-filter: blur(12px);
                background: rgba(255, 255, 255, 0.5);
                border-bottom: 1px solid var(--glass-border);
                padding: 1.5rem 2rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
                position: sticky;
                top: 0;
                z-index: 10;
                box-shadow: 0 4px 30px rgba(0, 0, 0, 0.03);
            }

            .logo {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                font-weight: 800;
                font-size: 1.6rem;
                color: var(--chocolate);
                letter-spacing: -0.5px;
            }

            .logo span {
                color: var(--pink-primary);
            }

            .logo-icon {
                font-size: 2.2rem;
                animation: spin 12s linear infinite;
            }

            @keyframes spin {
                100% { transform: rotate(360deg); }
            }

            main {
                max-width: 1200px;
                margin: 3rem auto;
                padding: 0 1.5rem;
                position: relative;
                z-index: 1;
            }

            .dashboard-title {
                font-size: 2.5rem;
                font-weight: 800;
                margin-bottom: 2rem;
                color: var(--chocolate);
                text-align: center;
            }

            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
                gap: 2rem;
            }

            /* Glassmorphism Card Style */
            .card {
                background: var(--glass-bg);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid var(--glass-border);
                border-radius: 24px;
                padding: 2rem;
                box-shadow: 0 8px 32px 0 rgba(255, 107, 139, 0.08);
                transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                position: relative;
                overflow: hidden;
            }

            .card:hover {
                transform: translateY(-8px) scale(1.02);
                box-shadow: 0 12px 40px 0 rgba(255, 107, 139, 0.15);
            }

            .card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 6px;
                background: linear-gradient(90deg, var(--pink-primary), var(--yellow-gold));
            }

            .card-header {
                margin-bottom: 1.25rem;
            }

            .card-title {
                font-size: 1.4rem;
                font-weight: 800;
                color: var(--chocolate);
                margin-bottom: 0.5rem;
            }

            .card-subtitle {
                font-size: 0.85rem;
                color: #7b6567;
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }

            .card-body {
                margin-bottom: 2rem;
                background: rgba(255, 255, 255, 0.4);
                border-radius: 16px;
                padding: 1.25rem;
                border: 1px solid rgba(255, 255, 255, 0.5);
            }

            .field-row {
                display: flex;
                margin-bottom: 0.75rem;
                font-size: 0.95rem;
            }

            .field-row:last-child {
                margin-bottom: 0;
            }

            .field-label {
                font-weight: 600;
                width: 100px;
                color: var(--chocolate);
                flex-shrink: 0;
            }

            .field-value {
                color: #4a3c3e;
            }

            .price-badge {
                display: inline-block;
                background: var(--pink-light);
                color: var(--pink-primary);
                font-weight: 800;
                padding: 0.25rem 0.75rem;
                border-radius: 12px;
                font-size: 1.1rem;
                border: 1px solid rgba(255, 107, 139, 0.2);
            }

            .actions {
                display: flex;
                gap: 1rem;
            }

            button {
                flex: 1;
                border: none;
                padding: 0.85rem;
                border-radius: 16px;
                font-weight: 700;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
            }

            .btn-approve {
                background: var(--success-green);
                color: white;
                box-shadow: 0 4px 15px rgba(46, 196, 182, 0.3);
            }

            .btn-approve:hover {
                background: #25a89c;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(46, 196, 182, 0.4);
            }

            .btn-reject {
                background: #ff5c5c;
                color: white;
                box-shadow: 0 4px 15px rgba(255, 92, 92, 0.3);
            }

            .btn-reject:hover {
                background: #e04e4e;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(255, 92, 92, 0.4);
            }

            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none !important;
                box-shadow: none !important;
            }

            /* Loader animations */
            .spinner {
                width: 18px;
                height: 18px;
                border: 3px solid rgba(255,255,255,0.3);
                border-radius: 50%;
                border-top-color: white;
                animation: spin 1s ease-in-out infinite;
                display: none;
            }

            /* Empty state card */
            .empty-state {
                grid-column: 1 / -1;
                background: var(--glass-bg);
                backdrop-filter: blur(16px);
                border: 1px solid var(--glass-border);
                border-radius: 32px;
                padding: 4rem 2rem;
                text-align: center;
                box-shadow: 0 8px 32px 0 rgba(255, 107, 139, 0.05);
            }

            .empty-icon {
                font-size: 5rem;
                margin-bottom: 1.5rem;
                display: inline-block;
                animation: bounce 2s infinite ease-in-out;
            }

            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-15px); }
            }

            .empty-state h3 {
                font-size: 1.8rem;
                font-weight: 800;
                color: var(--chocolate);
                margin-bottom: 0.5rem;
            }

            .empty-state p {
                color: #7b6567;
                font-size: 1.1rem;
            }

            /* Slide-out Modal */
            .modal-backdrop {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(45, 35, 37, 0.4);
                backdrop-filter: blur(6px);
                z-index: 100;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }

            .modal-backdrop.active {
                opacity: 1;
                visibility: visible;
            }

            .modal {
                position: fixed;
                top: 0;
                right: -460px;
                width: 100%;
                max-width: 460px;
                height: 100%;
                background: white;
                box-shadow: -10px 0 40px rgba(0,0,0,0.1);
                z-index: 101;
                transition: right 0.4s cubic-bezier(0.16, 1, 0.3, 1);
                display: flex;
                flex-direction: column;
                border-top-left-radius: 32px;
                border-bottom-left-radius: 32px;
                overflow: hidden;
            }

            .modal.active {
                right: 0;
            }

            .modal-header {
                padding: 2rem;
                background: linear-gradient(135deg, var(--pink-light), #ffe5ec);
                border-bottom: 1px solid rgba(255, 107, 139, 0.1);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }

            .modal-title {
                font-weight: 800;
                font-size: 1.4rem;
                color: var(--chocolate);
            }

            .modal-close {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 107, 139, 0.2);
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 1.2rem;
                color: var(--chocolate);
                transition: all 0.2s;
            }

            .modal-close:hover {
                background: var(--pink-primary);
                color: white;
            }

            .modal-body {
                padding: 2rem;
                flex: 1;
                overflow-y: auto;
            }

            .compliance-review-title {
                font-weight: 800;
                font-size: 1.2rem;
                margin-bottom: 1rem;
                color: var(--pink-primary);
            }

            .compliance-text {
                font-size: 1.05rem;
                line-height: 1.6;
                color: #3d3335;
                white-space: pre-line;
                background: var(--pink-light);
                padding: 1.5rem;
                border-radius: 20px;
                border: 1px solid rgba(255, 107, 139, 0.15);
            }
        </style>
    </head>
    <body>
        <div class="glow-1"></div>
        <div class="glow-2"></div>

        <header>
            <div class="logo">
                <div class="logo-icon">🍩</div>
                <div>Donut<span>Store</span></div>
            </div>
            <div>
                <span style="font-weight: 600; color: var(--chocolate);">Manager Console</span>
            </div>
        </header>

        <main>
            <h1 class="dashboard-title">Pending Expense Approvals</h1>

            <div class="grid" id="pending-grid">
                <!-- Pending items will be rendered here -->
            </div>
        </main>

        <!-- Slide-out Modal -->
        <div class="modal-backdrop" id="modal-backdrop" onclick="closeModal()">
            <div class="modal" id="modal" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <div class="modal-title">Action Processed</div>
                    <button class="modal-close" onclick="closeModal()">×</button>
                </div>
                <div class="modal-body">
                    <div class="compliance-review-title">Agent Compliance Review</div>
                    <div class="compliance-text" id="compliance-review-text">
                        Processing final compliance checks...
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function fetchPending() {
                const grid = document.getElementById('pending-grid');
                grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; font-size: 1.2rem; font-weight: 600; color: var(--chocolate);">Loading pending approvals...</div>';

                try {
                    const response = await fetch('/api/pending');
                    const data = await response.json();

                    if (data.length === 0) {
                        grid.innerHTML = `
                            <div class="empty-state">
                                <div class="empty-icon">🎉</div>
                                <h3>All Caught Up!</h3>
                                <p>No pending expense reports require your approval.</p>
                            </div>
                        `;
                        return;
                    }

                    grid.innerHTML = '';
                    data.forEach(item => {
                        const amountStr = item.amount ? `$${parseFloat(item.amount).toFixed(2)}` : 'N/A';
                        const card = document.createElement('div');
                        card.className = 'card';
                        card.id = `card-${item.session_id}`;
                        card.innerHTML = `
                            <div class="card-header">
                                <div class="card-title">${item.description || 'Expense Report'}</div>
                                <div class="card-subtitle">
                                    <span>Session: ${item.session_id}</span>
                                    <span>Interrupt ID: ${item.interrupt_id}</span>
                                </div>
                            </div>
                            <div class="card-body">
                                <div class="field-row">
                                    <div class="field-label">Amount:</div>
                                    <div class="field-value"><span class="price-badge">${amountStr}</span></div>
                                </div>
                                <div class="field-row" style="margin-top: 1rem;">
                                    <div class="field-label">Reason:</div>
                                    <div class="field-value">${item.reason || 'No explanation provided.'}</div>
                                </div>
                            </div>
                            <div class="actions">
                                <button class="btn-approve" id="approve-btn-${item.session_id}" onclick="takeAction('${item.session_id}', '${item.interrupt_id}', true)">
                                    <span class="spinner" id="approve-spinner-${item.session_id}"></span>
                                    <span>Approve</span>
                                </button>
                                <button class="btn-reject" id="reject-btn-${item.session_id}" onclick="takeAction('${item.session_id}', '${item.interrupt_id}', false)">
                                    <span class="spinner" id="reject-spinner-${item.session_id}"></span>
                                    <span>Reject</span>
                                </button>
                            </div>
                        `;
                        grid.appendChild(card);
                    });
                } catch (error) {
                    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: red;">Failed to load approvals: ${error.message}</div>`;
                }
            }

            async function takeAction(sessionId, interruptId, approved) {
                // Show loading state
                const approveBtn = document.getElementById(`approve-btn-${sessionId}`);
                const rejectBtn = document.getElementById(`reject-btn-${sessionId}`);
                const spinnerId = approved ? `approve-spinner-${sessionId}` : `reject-spinner-${sessionId}`;
                const spinner = document.getElementById(spinnerId);

                approveBtn.disabled = true;
                rejectBtn.disabled = true;
                spinner.style.display = 'block';

                try {
                    const response = await fetch(`/api/action/${sessionId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            interrupt_id: interruptId,
                            approved: approved
                        })
                    });

                    const result = await response.json();

                    if (response.ok) {
                        // Open modal and show compliance text
                        document.getElementById('compliance-review-text').innerText = result.response || "Decision processed successfully.";
                        openModal();
                        // Refresh pending list
                        fetchPending();
                    } else {
                        alert("Error processing action: " + (result.detail || "Unknown error"));
                        approveBtn.disabled = false;
                        rejectBtn.disabled = false;
                        spinner.style.display = 'none';
                    }
                } catch (error) {
                    alert("Network error processing action: " + error.message);
                    approveBtn.disabled = false;
                    rejectBtn.disabled = false;
                    spinner.style.display = 'none';
                }
            }

            function openModal() {
                document.getElementById('modal-backdrop').classList.add('active');
                document.getElementById('modal').classList.add('active');
            }

            function closeModal() {
                document.getElementById('modal-backdrop').classList.remove('active');
                document.getElementById('modal').classList.remove('active');
            }

            // Fetch on page load
            window.onload = fetchPending;
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/pending")
async def get_pending():
    project, location, engine_id = parse_runtime_id(AGENT_RUNTIME_ID, PROJECT_ID, LOCATION)
    if not project or not engine_id:
        raise HTTPException(
            status_code=500,
            detail="GCP project and AGENT_RUNTIME_ID environment variables must be set."
        )

    try:
        session_service = VertexAiSessionService(
            project=project,
            location=location,
            agent_engine_id=engine_id
        )

        list_res = await session_service.list_sessions(app_name="app")
        pending_items = []

        for session in list_res.sessions:
            full_session = await session_service.get_session(
                app_name="app",
                user_id=session.user_id,
                session_id=session.id
            )
            if not full_session or not full_session.history:
                continue

            for i, event in enumerate(full_session.history):
                # Search for model_turn where the model requests input
                if event.event_type == 'model_turn' and event.content and event.content.parts:
                    for part in event.content.parts:
                        fc = part.function_call
                        if fc and fc.name == 'adk_request_input':
                            interrupt_id = event.id

                            # Identify if there is a corresponding response event in subsequent history
                            resolved = False
                            for next_event in full_session.history[i+1:]:
                                if next_event.content and next_event.content.parts:
                                    for next_part in next_event.content.parts:
                                        fr = next_part.function_response
                                        if fr and fr.name == 'adk_request_input' and fr.id == interrupt_id:
                                            resolved = True
                                            break
                                if resolved:
                                    break

                            if not resolved:
                                pending_items.append({
                                    "session_id": session.id,
                                    "interrupt_id": interrupt_id,
                                    "amount": fc.args.get("amount"),
                                    "description": fc.args.get("description"),
                                    "reason": fc.args.get("reason"),
                                    "args": fc.args
                                })
        return pending_items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/action/{session_id}")
async def take_action(session_id: str, request: ActionRequest):
    project, location, engine_id = parse_runtime_id(AGENT_RUNTIME_ID, PROJECT_ID, LOCATION)
    if not project or not engine_id:
        raise HTTPException(
            status_code=500,
            detail="GCP project and AGENT_RUNTIME_ID environment variables must be set."
        )

    try:
        # Initialize vertexai
        vertexai.init(project=project, location=location)

        client = vertexai.Client(project=project, location=location)
        agent = client.agent_engines.get(name=f"projects/{project}/locations/{location}/reasoningEngines/{engine_id}")

        # Construct resume payload directly to avoid duplicate parameter errors on the ADK runner
        resume_payload = {
            "role": "user",
            "parts": [
                {
                    "function_response": {
                        "id": request.interrupt_id,
                        "name": "adk_request_input",
                        "response": {"approved": request.approved}
                    }
                }
            ]
        }

        # Run query asynchronously, strictly setting user_id to "default-user" to avoid ownership mismatch
        response = await agent.async_query(
            message=resume_payload,
            session_id=session_id,
            user_id="default-user"
        )

        return {"status": "success", "response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
