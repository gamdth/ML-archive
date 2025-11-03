
from flask import Flask, render_template, request, send_file
import io
import matplotlib.pyplot as plt

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('hi.html')

@app.route('/chart')
def chart():
    chart_type = request.args.get('type', 'bar')

    plt.figure(figsize=(5,3))
    x = ['A', 'B', 'C', 'D']
    y = [10, 15, 7, 12]

    if chart_type == 'bar':
        plt.bar(x, y, color='#8353A5')
    elif chart_type == 'line':
        plt.plot(x, y, color='#F6B4C9', marker='o')
    else:
        plt.pie(y, labels=x, autopct='%1.1f%%')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)

