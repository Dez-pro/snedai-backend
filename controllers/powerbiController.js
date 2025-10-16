import dotenv from "dotenv";
import fetch from "node-fetch";
dotenv.config();

// Génère un token AAD (client credentials) via MSAL simple (fetch token endpoint)
async function getAzureAdAccessToken() {
  const tenantId = process.env.POWERBI_TENANT_ID;
  const clientId = process.env.POWERBI_CLIENT_ID;
  const clientSecret = process.env.POWERBI_CLIENT_SECRET;

  const url = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`;
  const body = new URLSearchParams({
    client_id: clientId,
    client_secret: clientSecret,
    scope: "https://analysis.windows.net/powerbi/api/.default",
    grant_type: "client_credentials",
  });

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`AAD token error: ${res.status} ${text}`);
  }
  const data = await res.json();
  return data.access_token;
}

export const getEmbedConfig = async (req, res) => {
  try {
    const groupId = req.query.groupId || process.env.POWERBI_WORKSPACE_ID;
    const reportId = req.query.reportId || process.env.POWERBI_REPORT_ID;
    const datasetId = req.query.datasetId || process.env.POWERBI_DATASET_ID;
    if (!groupId || !reportId || !datasetId) {
      return res.status(400).json({ success: false, message: "Missing Power BI IDs (groupId/reportId/datasetId)" });
    }

    const aadToken = await getAzureAdAccessToken();

    // Récupérer l'embedUrl du report
    const reportRes = await fetch(`https://api.powerbi.com/v1.0/myorg/groups/${groupId}/reports/${reportId}`, {
      headers: { Authorization: `Bearer ${aadToken}` },
    });
    if (!reportRes.ok) {
      const text = await reportRes.text();
      throw new Error(`Get report error: ${reportRes.status} ${text}`);
    }
    const report = await reportRes.json();
    const embedUrl = report?.embedUrl;

    // Générer un embed token en lecture seule
    const genRes = await fetch(`https://api.powerbi.com/v1.0/myorg/groups/${groupId}/reports/${reportId}/GenerateToken`, {
      method: "POST",
      headers: { Authorization: `Bearer ${aadToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        datasets: [{ id: datasetId }],
        reports: [{ id: reportId }],
        targetWorkspaces: [{ id: groupId }],
        accessLevel: "View",
      }),
    });
    if (!genRes.ok) {
      const text = await genRes.text();
      throw new Error(`GenerateToken error: ${genRes.status} ${text}`);
    }
    const tokenData = await genRes.json();

    res.json({ success: true, embedUrl, accessToken: tokenData?.token, expiration: tokenData?.expiration, reportId, groupId, datasetId });
  } catch (err) {
    console.error(err);
    res.status(500).json({ success: false, message: err.message });
  }
};


