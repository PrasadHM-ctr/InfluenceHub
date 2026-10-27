const API_URL = "http://127.0.0.1:8000/api";

// -----------------------------
// Register User
// -----------------------------
export async function registerUser(data: {
  username: string;
  email: string;
  password: string;
}) {
  const response = await fetch(`${API_URL}/register/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(JSON.stringify(result));
  }

  return result;
}

// -----------------------------
// Login User
// -----------------------------
export async function loginUser(
  username: string,
  password: string
) {
  const response = await fetch(`${API_URL}/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      password,
    }),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(JSON.stringify(result));
  }

  return result;
}

// -----------------------------
// Get User Profile (Protected API)
// -----------------------------
export async function getProfile() {
  const token = localStorage.getItem("access");

  const response = await fetch(`${API_URL}/profile/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return response.json();
}

// -----------------------------
// Get Campaigns (Protected API)
// -----------------------------
export async function getCampaigns() {
  const token = localStorage.getItem("access");

  const response = await fetch(`${API_URL}/campaigns/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result?.detail || "Failed to fetch campaigns");
  }

  return result;
}

// -----------------------------
// Accept Campaign Request
// -----------------------------
export async function acceptCampaign(id: number) {
  const token = localStorage.getItem("access");

  const response = await fetch(`${API_URL}/campaigns/${id}/accept/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result?.detail || "Failed to accept campaign");
  }

  return result;
}

// -----------------------------
// Reject Campaign Request
// -----------------------------
export async function rejectCampaign(id: number) {
  const token = localStorage.getItem("access");

  const response = await fetch(`${API_URL}/campaigns/${id}/reject/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result?.detail || "Failed to reject campaign");
  }

  return result;
}