from flask import Flask, render_template, url_for, request
from util.pagination import Pagination

from datetime import datetime
import requests
import sys

app = Flask(__name__)

AGENCIES = {
        'Department of Health and Human Services': 'HHS',
        'National Science Foundation': 'NSF',
}

SOLICITATIONS_PER_PAGE = 20
FBOPEN_URI = 'http://fbopen-lb1-1729291742.us-west-2.elb.amazonaws.com:3000/v0/opp'

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/solicitations', defaults={'page': 1})
@app.route('/solicitations/<int:page>')
def solicitations(page):
    user_search_terms = request.args.get('search')

    if user_search_terms:
        page = 1

    offset = Pagination.offset(page, SOLICITATIONS_PER_PAGE)
    print offset
    
    search_terms = '(sbir OR "small business innovation research")'
    all_search_terms = ''
    if user_search_terms:
        all_search_terms = ' AND '.join([search_terms, user_search_terms])
    else:
        all_search_terms = search_terms
    print all_search_terms
    
    columns = 'description,title,summary,listing_url,solnbr,office,agency,close_dt,open_dt,posted_dt'
    r = requests.get(FBOPEN_URI, params={'q': all_search_terms, 'start': offset, 'rows': SOLICITATIONS_PER_PAGE, 'fl': columns})
    print r.request.url

    count = r.json()['response']['numFound']
    pagination = Pagination(page, SOLICITATIONS_PER_PAGE, count)

    results = _get_results(r)

    no_results_msg = 'No results found' if not len(results) > 0 else ''

    for obj in results:
        _parse_obj_dates(obj, 'close_dt', 'open_dt', 'posted_dt')
        _abbreviate_agency(obj)

    return render_template("solicitations.html", pager=pagination, results=results, no_results_msg=no_results_msg)


@app.route('/solicitations/<id>')
def solicitation(id):
    r = requests.get(FBOPEN_URI, params={'q': 'solnbr:{}'.format(id.upper()), 'rows': 1})
    obj = _get_results(r)[0]

    _parse_obj_dates(obj, 'close_dt', 'open_dt', 'posted_dt')
    _abbreviate_agency(obj)

    #program_year = obj['close_dt'].year

    return render_template("solicitation.html", id=id, obj=obj)


def _get_results(raw):
    return raw.json().get('response').get('docs')


def _parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')


def _parse_obj_date(obj, key):
    if obj.has_key(key):
        obj[key] = _parse_date(obj[key])


def _parse_obj_dates(obj, *keys):
    for key in keys:
        _parse_obj_date(obj, key)

def _abbreviate_agency(obj):
    if obj.has_key('agency'):
        obj['agency_abbr'] = AGENCIES.get(obj['agency'], obj['agency'])

@app.template_filter('datetime')
def datetimeformat(value, format='%m/%d/%Y'):
    if value:
        return value.strftime(format)
    else:
        return ''

def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

app.jinja_env.globals['url_for_other_page'] = url_for_other_page


if __name__ == "__main__":
    app.secret_key = 'f81f8225bb1a4f5681a7e72d1fc0a764'
    app.run(debug=True)
