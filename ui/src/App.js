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
	this.keys.forEach(function(key) {
	    $.ajaxQueue({
		url: 'api/' + key,
		type: 'GET',
		success: function(result) {
		    var values = function() {
			var values = []
			result.data.forEach(function(row) {
			    values.push([
				Date.parse(row.timestamp),
				row.value
			    ]);
			});
			return values;
		    }();
		    data.push({
			name: key,
			data: values
		    });
		    
		    component.setState({
			data: {
			    chart: {
				type: 'spline'
			    },
			    title: {
				text: "Sentiment analysis"
			    },
			    subtitle: {
				text: "..."
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
	    });
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
	<Chart keys={["trump"]}/>
      </div>);
  }
}

export default App;
