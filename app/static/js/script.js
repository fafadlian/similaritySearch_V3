// app/static/js/script.js
// Vanilla JS to handle the search form and display results via POST to match backend

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('search-form');
  const resultsDiv = document.getElementById('results');
  const submitBtn = document.getElementById('submit-btn');

  if (!form) {
    console.error('Search form not found');
    return;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    resultsDiv.innerHTML = '<p class="loading">Searching...</p>';
    submitBtn.disabled = true;

    // Gather form data into JSON payload matching CombinedRequest schema
    const formData = new FormData(form);
    const payload = {};
    formData.forEach((value, key) => {
      // Convert threshold fields to numbers
      if (key === 'nameThreshold' || key === 'ageThreshold') {
        payload[key] = parseFloat(value) || 0;
      } else {
        payload[key] = value;
      }
    });

    try {
      const response = await fetch('/combined_operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      if (result.status === 'success') {
        renderTable(result.data);
      } else {
        resultsDiv.innerHTML = `<p class="error">${result.message}</p>`;
      }
    } catch (err) {
      resultsDiv.innerHTML = `<p class="error">Network error: ${err.message}</p>`;
    } finally {
      submitBtn.disabled = false;
    }
  });

  function renderTable(data) {
    if (!Array.isArray(data) || data.length === 0) {
      resultsDiv.innerHTML = '<p>No similar passengers found.</p>';
      return;
    }

    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const tbody = document.createElement('tbody');

    // use keys from first record
    const headers = Object.keys(data[0]);
    const headerRow = document.createElement('tr');
    headers.forEach(key => {
      const th = document.createElement('th');
      th.textContent = key;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    data.forEach(record => {
      const row = document.createElement('tr');
      headers.forEach(key => {
        const td = document.createElement('td');
        td.textContent = record[key] != null ? record[key] : '';
        row.appendChild(td);
      });
      tbody.appendChild(row);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    resultsDiv.innerHTML = '';
    resultsDiv.appendChild(table);
  }
});
