fetch('http://127.0.0.1:8000/api/social/community-feed', {
  headers: { 'Authorization': 'Bearer mock_token' }
}).then(r => r.json().then(data => console.log(r.status, data)).catch(e => {
  console.log(r.status, "Failed to parse json");
  r.text().then(t => console.log(t));
})).catch(e => console.error(e));
