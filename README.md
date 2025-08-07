# django-gen-ai-examples
<p>A Django project that showcases Gen AI Implementations.</p>
<p>Demo Hosted at: https://saravananramanathan.pythonanywhere.com/home/ # Disabled. Not Enough Recources to maintain.</p> 
<p>Stack: Django4 + Vue3.</p>

# Local setup:

<ul>
  <li>
    <span>Clone the repo.</span>
  </li>
  <li>
    <span>Create a <code>.env</code> using <code>.env_example</code>. Setup <code>.env</code> </span>
  </li>
  <li>
    <span>build docker image: <code>docker compose build</code></span>
  </li>
  <li>
    <span>Start containers: <code>docker compose up</code></span>
  </li>
  <li>
    <span>exec into backend: <code>docker exec -it gen_ai_training_backend bash</code> and follow the steps below:</span>
    <ul>
      <li>Create super user: <code>./manage.py createsuperuser</code> -- you will need this to log into Django Admin.</li>
      <li>Imprort prompt templates from Fixtures: <code>./manage.py reload_prompt_templates --skip-confirmation</code></li>
      <li>[Optional] Load data from Eng dictionary fixture: <code>./manage.py loaddata ./fixtures/eng_dictionary_fixture.json</code></li>
      <li>[Optional] Generate init embedding: <code>./manage.py generate_dictionary_embeddings</code> -- NOTE: This can take some Time.</li>
    </ul>
  </li>
  <li>
    <span>Application can be accessed at <code>chat.local</code> or <code>http://0.0.0.0:8220/</code></span>
  </li>
  <li>
    <span>Airflow can be accessed at <code>airflow.local</code> or <code>http://0.0.0.0:8080/</code> default credentails: <code>admin/admin</code></span>
  </li>
  <li>
    <span>Flower dashboard can be accessed at <code>flower.local</code> or <code>http://0.0.0.0:5555/</code></span>
  </li>
  <li>
    <span>Google OAuth</span>
    <ul>
      <li>In Google Developer Console [GDC] create an <code>OAuth 2.0 Client ID</code> with type as <code>Web application</code></li>
      <li>In GDC, add Authorized redirect URIs for the created OAuth Client. -- for dev it can point to your localhost.</li>
      <li>Make sure to download the CREDENTIALS JSON key and store it somewhere safe, we will need it later.</li>
    </ul>
  </li>
  <li>
    <span>Django Allauth setup</span>
    <ul>
      <li>Go to: <code>http://localhost:8220/admin/socialaccount/socialapp/</code> and create/add new social application.</li>
      <li>Use the following format:<img width="952" height="382" alt="Screenshot 2025-08-07 at 2 26 51 PM" src="https://github.com/user-attachments/assets/f5be1259-fda7-4e22-b839-91db1fbc3052" />
</li>
    </ul>
  </li>
</ul>

