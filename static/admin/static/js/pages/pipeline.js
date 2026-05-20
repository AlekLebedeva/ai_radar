/**
 * AI RADAR — Pipeline Page
 */

async function loadPipeline() {
    try {
        const data = await api('/pipeline');
        renderPipeline(data);
    } catch (err) {
        console.error('Pipeline load error:', err);
        showToast('Ошибка загрузки pipeline', 'error');
    }
}

function renderPipeline(data) {
    const container = document.getElementById('pipeline-visual');
    const colors = { idle: '#64748b', running: '#3b82f6', completed: '#10b981', failed: '#ef4444' };
    const nodePositions = {};
    const svgWidth = 800, svgHeight = 400;
    const nodeWidth = 140, nodeHeight = 50;

    const sources = data.nodes.filter(n => n.node_id.startsWith('source_'));
    const stages = data.nodes.filter(n => !n.node_id.startsWith('source_'));

    let svg = `<svg class="pipeline-svg" viewBox="0 0 ${svgWidth} ${svgHeight}">`;

    const sourceX = 60;
    const sourceSpacing = svgHeight / (sources.length + 1);
    sources.forEach((node, i) => {
        const y = sourceSpacing * (i + 1) - nodeHeight / 2;
        nodePositions[node.node_id] = { x: sourceX, y: y + nodeHeight / 2 };
    });

    const stageXStart = 280;
    const stageSpacing = (svgWidth - stageXStart - 100) / (stages.length - 1 || 1);
    stages.forEach((node, i) => {
        const x = stageXStart + stageSpacing * i;
        const y = svgHeight / 2;
        nodePositions[node.node_id] = { x: x + nodeWidth / 2, y };
    });

    data.edges.forEach(edge => {
        const from = nodePositions[edge.from_node];
        const to = nodePositions[edge.to_node];
        if (from && to) {
            svg += `<line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" stroke="#334155" stroke-width="2" stroke-dasharray="4"/>`;
            const angle = Math.atan2(to.y - from.y, to.x - from.x);
            const arrowLen = 8;
            const ax = to.x - arrowLen * Math.cos(angle);
            const ay = to.y - arrowLen * Math.sin(angle);
            svg += `<polygon points="${to.x},${to.y} ${ax-4},${ay-4} ${ax-4},${ay+4}" fill="#334155" transform="rotate(${angle * 180 / Math.PI}, ${to.x}, ${to.y})"/>`;
        }
    });

    data.nodes.forEach(node => {
        const pos = nodePositions[node.node_id];
        if (!pos) return;
        const isSource = node.node_id.startsWith('source_');
        const w = isSource ? 120 : nodeWidth;
        const h = nodeHeight;
        const x = pos.x - w / 2;
        const y = pos.y - h / 2;
        const color = colors[node.status] || colors.idle;
        svg += `
            <g class="pipeline-node">
                <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="${color}20" stroke="${color}" stroke-width="2"/>
                <text x="${pos.x}" y="${pos.y - 4}" text-anchor="middle" fill="${color}" font-size="12" font-weight="600">${node.label}</text>
                <text x="${pos.x}" y="${pos.y + 12}" text-anchor="middle" fill="#94a3b8" font-size="10">${node.count} items</text>
            </g>`;
    });

    svg += '</svg>';
    container.innerHTML = svg;
}
