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
      <li>Load data from Eng dictionary fixture: <code>./manage.py loaddata ./fixtures/eng_dictionary_fixture.json</code></li>
      <li>Generate init embedding: <code>./manage.py generate_dictionary_embeddings</code> -- NOTE: This can take some Time.</li>
    </ul>
  </li>
  <li>
    <span>Application can be accessed at <code>chat.local</code> or <code>http://0.0.0.0:8220/</code></span>
  </li>
</ul>

