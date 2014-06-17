var FlexibleUrlDatasource = function (options) {
    this._formatter = options.formatter;
    this._columns = options.columns;
    this._formatter = options.formatter;

    this._url = options.url;

};

FlexibleUrlDatasource.prototype = {

    columns: function () {
        return this._columns;
    },

    data: function (options, callback) {
        var self = this;
        if (jQuery.isFunction(self._url)) {
            var url = this._url()
        }
        else {
            var url = this._url;
        }

        $.ajax(url, {
            dataType: 'json',
            type: 'GET'
        }).done(function (response) {
            var data = response;
            var count = response.length;
            var startIndex = options.pageIndex * options.pageSize;
            var endIndex = startIndex + options.pageSize;
            var end = (endIndex > count) ? count : endIndex;
            var pages = Math.ceil(count / options.pageSize);
            var page = options.pageIndex + 1;
            var start = startIndex + 1;
            // TODO: slice and dice server side
            data = data.slice(startIndex, endIndex);
            if (self._formatter) self._formatter(data);
            callback({ data: data, start: start, end: end, count: count, pages: pages, page: page });
        });
    }
};