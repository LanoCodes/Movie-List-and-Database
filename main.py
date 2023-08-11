from flask import Flask, render_template, redirect, url_for
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests

db = SQLAlchemy()
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movie-list.db'
Bootstrap5(app)
db.init_app(app)

tmdb_ACCESS_TOKEN = '*** INCLUDE YOUR OWN ACCESS TOKEN HERE ***'

url_tmdb_search = 'https://api.themoviedb.org/3/search/movie'
url_tmdb_find_by_id = 'https://api.themoviedb.org/3/movie/'
base_image_url = 'https://image.tmdb.org/t/p/w500'
search_results = []

# Outlining how that database should look
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Title is unique so that we only get one entry per movie title in the ranking
    title = db.Column(db.String, unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float)
    ranking = db.Column(db.Integer)
    review = db.Column(db.String)
    img_url = db.Column(db.String, nullable=False)

class RateMovieForm(FlaskForm):
    rating = StringField(label='Your Rating Out of 10 e.g. 8.3', validators=[DataRequired()])
    review = StringField(label='Your Review', validators=[DataRequired()])
    submit = SubmitField(label='Done')

class AddMovieForm(FlaskForm):
    title = StringField(label='Movie Title', validators=[DataRequired()])
    submit = SubmitField(label='Add Movie')

@app.route("/")
def home():
    with app.app_context():
        result = db.session.execute(db.select(Movie).order_by(Movie.rating))
        all_movies = result.scalars()
        movie_list = []

        for movie in all_movies:
            movie_list.append(movie)

        for movie in movie_list:
            movie.ranking = len(movie_list) - movie_list.index(movie)

    return render_template(
        "index.html",
        movies=movie_list
    )

@app.route('/update/<movie_id>', methods=['POST', 'GET'])
def update(movie_id):
    rating_form = RateMovieForm()

    if rating_form.validate_on_submit():
        movie_to_update = db.get_or_404(Movie, movie_id)
        movie_to_update.rating = rating_form.rating.data
        movie_to_update.review = rating_form.review.data
        db.session.commit()

        return redirect(url_for('home'))


    return render_template(
        'edit.html',
        form= rating_form
    )

@app.route('/delete/<movie_id>')
def delete(movie_id):

    movie_to_delete = db.get_or_404(Movie, movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()

    return redirect(url_for('home'))

@app.route('/add', methods=['POST', 'GET'])
def add():
    add_form = AddMovieForm()
    if add_form.validate_on_submit():
        movie_title = add_form.title.data
        # USing the retrieved movie title, I can now go get the search result from the tmdb API
        params = {
            'query': movie_title,
            'include_adult': False,
            'language': 'en-US',
            'page': 1
        }
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {tmdb_ACCESS_TOKEN}'
        }
        response = requests.get(url=url_tmdb_search, headers=headers, params=params)
        global  search_results
        search_results = response.json()['results']

        return redirect(url_for('select'))

    return render_template(
        'add.html',
        form=add_form
    )

@app.route('/select/')
def select():
    return render_template(
        'select.html',
        search_results=search_results
    )

@app.route('/choice/<movie_id>')
def choice(movie_id):
    print(f'Movie ID that should\'ve been passed through: {movie_id}')

    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {tmdb_ACCESS_TOKEN}'
    }
    params = {
        'language': 'en-US'
    }
    movie_id_url = url_tmdb_find_by_id + movie_id
    response = requests.get(url=movie_id_url, headers=headers, params=params)
    print(f'Response code from TMDB: {response.status_code}')
    movie_info = response.json()

    movie_title = movie_info['title']
    movie_img_url = base_image_url + movie_info['poster_path']
    movie_year = movie_info['release_date'].split('-')[0]
    movie_descr = movie_info['overview']

    db.create_all()
    new_movie = Movie(
        title = movie_title,
        year = movie_year,
        description = movie_descr,
        img_url = movie_img_url,
    )
    print(f'Movie ID BEFORE Movie object added to DB: {new_movie.id}')
    db.session.add(new_movie)
    db.session.commit()
    print(f'Movie ID AFTER Movie object should\'ve been added to DB: {new_movie.id}')


    return redirect(url_for('update', movie_id=new_movie.id))

if __name__ == '__main__':
    app.run(debug=True)
