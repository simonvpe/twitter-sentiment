import React, { Component } from 'react';
import ReactHighcharts from 'react-highcharts';
import $ from 'jquery';
import logo from './logo.svg';
import './App.css';


var ajaxQueue = $({})
$.ajaxQueue = function(ajaxOpts) {
    var oldComplete = ajaxOpts.complete;
    ajaxQueue.queue(function(next) {
	ajaxOpts.complete = function() {
	    if(oldComplete) oldComplete.apply(this, arguments);
	    next();
	};
	$.ajax(ajaxOpts);
    });
};

class Chart extends Component {
    constructor(props) {
	super(props)
	this.state = {data: null}
	this.keys = props.keys
	this.series = []
    }

    componentDidMount() {
	var component = this;
	var data = []

	var handleSeries = function(series) {

	    var values = function() {
		var values = []
		series.values.forEach(function(row) {
		    values.push({
			x: Date.parse(row[0]),
			y: row[0],
			std: row[2],
			tweetCount: row[3]
		    });
		});
		return values;
	    }();
		    
	    data.push({
		name: series.tags.key,
		data: values
	    });

	    component.setState({
		data: {
		    chart: {
			type: 'spline',
			zoomType: 'x'
		    },
		    title: {
			text: "Sentiment analysis"
		    },
		    subtitle: {
			text: "..."
		    },
		    tooltip: {
			formatter: function() {
			    return '' +
				'Sentiment; <b>' + this.point.y + '<b><br/>' +
				'Standard deviation: <b>' + this.point.std + '<b><br/>' +
				'Tweet count: <b>' + this.point.tweetCount + '<b><br/>'
			}
		    },
		    xAxis: {
			type: 'datetime',
			dateTimeLabelFormats: {
			    month: '%e. %b',
			    year: '%b'
			},
			title: {
			    text: 'Date'
			}
		    },
		    yAxis: {
			title: {
			    text: "Sentiment"
			}
		    },
		    plotOptions: {
			spline: {
			    marker: {
				enabled: true
			    }
			}
		    },
		    series: data	    
		}
	    });
	}
	
	$.ajaxQueue({
	    url: 'api/mean-sentiment',
            type: 'GET',
	    success: function(result) {
		result.series.forEach(handleSeries);
	    }
	});
    }
    
    render() {
	if (this.state.data) {
	    return <ReactHighcharts config = { this.state.data } />
	}
	return <div>Loading...</div>
    }
}

class App extends Component {
    render() {
	return (
		<div className="App">
		<div className="App-header">
		<img src={logo} className="App-logo" alt="logo" />
		<h2>Welcome to React</h2>
		</div>
		<Chart />
		</div>);
    }
}

export default App;
