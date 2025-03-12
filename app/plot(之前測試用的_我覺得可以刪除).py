from flask import Flask, request, render_templateimport requests
from clustering_visualization import umap_auto_tuning
from 2D_visualization import 2D_run

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('plot.html')


@app.route('/upload', methods=['POST'])
def upload():
    csv_file = request.files['file']
    df = pd.read_csv(csv_file).iloc[:, 1:]
    cluster_df = umap_auto_tuning(df)
    2D_cluster_df = 2D_run(cluster_df)
    
	


#data = requests.get('https://eodhistoricaldata.com/api/eod/AAPL.US?from=2020-01-05&to=2020-02-10&period=d&fmt=csv&api_token=OeAFFmMliFG5orCUuwAKQ8l4WWFQ67YX').text


#with open('file.csv', 'w') as f:
 #   f.write(data)
