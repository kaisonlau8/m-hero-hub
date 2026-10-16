/* feedback.js — Ant Design 交互反馈（无依赖）
 * message / notification：白底轻提示，文案由调用方传入（页面侧用中文）。
 * button.loading：提交按钮转圈，不改按钮原文。
 * 页面 Spin 由 html.ant-booting 控制，本脚本在文档解析完后撤下。
 * input[type=file][data-ant-upload="<url>"]：XHR 上传并显示进度。 */
(function () {
  'use strict';

  var LOADING_SVG = '<svg class="anticon-spin" viewBox="0 0 1024 1024" aria-hidden="true" focusable="false" fill="currentColor"><path d="M988 548c-19.9 0-36-16.1-36-36 0-59.4-11.6-117-34.6-171.3a440.45 440.45 0 00-94.3-139.9 437.71 437.71 0 00-139.9-94.3C629 83.6 571.4 72 512 72c-19.9 0-36-16.1-36-36s16.1-36 36-36c69.1 0 136.2 13.5 199.3 40.3C772.3 66 827 103 874 150c47 47 83.9 101.8 109.7 162.7 26.7 63.1 40.2 130.2 40.2 199.3.1 19.9-16 36-35.9 36z"/></svg>';

  var SPRITE = {
    success: '#i-check-circle',
    error: '#i-close-circle',
    warning: '#i-exclamation-circle',
    info: '#i-info-circle'
  };

  function spriteIcon(type) {
    var id = SPRITE[type] || SPRITE.info;
    return '<svg class="ai" aria-hidden="true"><use href="' + id + '"/></svg>';
  }

  function layer(className) {
    var el = document.querySelector('.' + className);
    if (!el) {
      el = document.createElement('div');
      el.className = className;
      document.body.appendChild(el);
    }
    return el;
  }

  function findKey(root, key) {
    if (!key) return null;
    var nodes = root.querySelectorAll('[data-key]');
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].getAttribute('data-key') === key) return nodes[i];
    }
    return null;
  }

  function removeEl(el) {
    if (!el || !el.parentNode) return;
    el.parentNode.removeChild(el);
  }

  function messageOpen(type, content, duration, key) {
    var root = layer('ant-message');
    var el = findKey(root, key);
    if (!el) {
      while (root.children.length >= 3) removeEl(root.firstChild);
      el = document.createElement('div');
      if (key) el.setAttribute('data-key', key);
      root.appendChild(el);
    }
    el.className = 'ant-message-notice ant-message-' + type;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    var icon = type === 'loading' ? LOADING_SVG : spriteIcon(type);
    el.innerHTML = '<div class="ant-message-notice-content"><span class="ant-message-icon">' + icon +
      '</span><span class="ant-message-text"></span></div>';
    el.querySelector('.ant-message-text').textContent = content == null ? '' : String(content);
    if (el._t) clearTimeout(el._t);
    var ms = duration == null ? (type === 'error' || type === 'warning' ? 4000 : 3000) : duration;
    if (ms > 0) el._t = setTimeout(function () { removeEl(el); }, ms);
    return function () { removeEl(el); };
  }

  function messageClose(key) {
    var root = document.querySelector('.ant-message');
    if (!root) return;
    if (!key) {
      while (root.firstChild) removeEl(root.firstChild);
      return;
    }
    removeEl(findKey(root, key));
  }

  var message = {
    success: function (c, d, k) { return messageOpen('success', c, d, k); },
    error: function (c, d, k) { return messageOpen('error', c, d, k); },
    info: function (c, d, k) { return messageOpen('info', c, d, k); },
    warning: function (c, d, k) { return messageOpen('warning', c, d, k); },
    loading: function (c, d, k) { return messageOpen('loading', c, d == null ? 0 : d, k); },
    close: messageClose
  };

  function notify(type, opts) {
    opts = opts || {};
    var title = opts.message || '';
    var desc = opts.description || '';
    var root = layer('ant-notification');
    var el = document.createElement('div');
    el.className = 'ant-notification-notice ant-notification-notice-' + type;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    el.innerHTML = '<span class="ant-notification-notice-icon">' + spriteIcon(type) + '</span>' +
      '<div class="ant-notification-notice-content"><div class="ant-notification-notice-message"></div>' +
      '<div class="ant-notification-notice-description"></div></div>' +
      '<button type="button" class="ant-notification-notice-close" aria-label="关闭">' +
      '<svg class="ai" aria-hidden="true"><use href="#i-close"/></svg></button>';
    el.querySelector('.ant-notification-notice-message').textContent = title;
    el.querySelector('.ant-notification-notice-description').textContent = desc;
    var close = function () { removeEl(el); };
    el.querySelector('.ant-notification-notice-close').addEventListener('click', close);
    root.appendChild(el);
    var ms = opts.duration == null ? 4500 : opts.duration;
    if (ms > 0) setTimeout(close, ms);
    return close;
  }

  var notification = {
    success: function (o) { return notify('success', o); },
    error: function (o) { return notify('error', o); },
    info: function (o) { return notify('info', o); },
    warning: function (o) { return notify('warning', o); },
    open: function (o) { return notify((o && o.type) || 'info', o); }
  };

  function setButtonLoading(btn, on) {
    if (!btn || btn.tagName === 'A') return;
    if (on) {
      if (btn.classList.contains('ant-btn-loading') || btn.disabled) return;
      btn.classList.add('ant-btn-loading');
      btn.setAttribute('aria-busy', 'true');
      if (!btn.querySelector('.ant-btn-loading-icon')) {
        var icon = document.createElement('span');
        icon.className = 'ant-btn-loading-icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.innerHTML = LOADING_SVG;
        btn.insertBefore(icon, btn.firstChild);
      }
      setTimeout(function () {
        if (btn.classList.contains('ant-btn-loading')) btn.disabled = true;
      }, 0);
    } else {
      btn.classList.remove('ant-btn-loading');
      btn.removeAttribute('aria-busy');
      var old = btn.querySelector('.ant-btn-loading-icon');
      if (old) old.remove();
      btn.disabled = false;
    }
  }

  function field(form, name) {
    var el = form.querySelector('[name="' + name + '"]');
    return el ? el.value : '';
  }

  function bindForms() {
    [].forEach.call(document.querySelectorAll('form'), function (form) {
      form.addEventListener('submit', function (e) {
        if (e.defaultPrevented) return;
        if (form.getAttribute('action') === '/account/password') {
          var nv = field(form, 'new');
          var n2 = field(form, 'new2');
          var oldv = field(form, 'old');
          if (nv !== n2) {
            e.preventDefault();
            message.error('两次输入的新密码不一致');
            return;
          }
          if (nv && oldv && nv === oldv) {
            e.preventDefault();
            message.error('新密码不能与当前密码相同');
            return;
          }
        }
        if (form.dataset.antSubmitting === '1') {
          e.preventDefault();
          return;
        }
        form.dataset.antSubmitting = '1';
        var btn = e.submitter;
        if (!btn || !form.contains(btn)) {
          btn = form.querySelector('button[type="submit"], button:not([type]), input[type="submit"]');
        }
        setButtonLoading(btn, true);
      });
    });
  }

  function bindLogout() {
    // 桌面下拉与移动端抽屉各有一处退出入口，都要弹出「正在退出登录」
    var links = document.querySelectorAll('#mhero-logout-link, #hub-drawer-logout');
    [].forEach.call(links, function (link) {
      link.addEventListener('click', function () {
        message.loading('正在退出登录…', 0, 'logout');
      });
    });
  }

  function bindUploads() {
    [].forEach.call(document.querySelectorAll('input[type="file"][data-ant-upload]'), function (input) {
      input.addEventListener('change', function () {
        var file = input.files && input.files[0];
        var url = input.getAttribute('data-ant-upload');
        if (!file || !url) return;
        var list = input.parentNode.querySelector('.ant-upload-list');
        if (!list) {
          list = document.createElement('div');
          list.className = 'ant-upload-list';
          input.parentNode.appendChild(list);
        }
        var item = document.createElement('div');
        item.className = 'ant-upload-list-item';
        item.innerHTML = '<div class="ant-upload-list-item-name"></div>' +
          '<div class="ant-progress ant-progress-line ant-progress-status-active">' +
          '<div class="ant-progress-outer"><div class="ant-progress-inner">' +
          '<div class="ant-progress-bg" style="width:0%"></div></div></div></div>';
        item.querySelector('.ant-upload-list-item-name').textContent = file.name;
        list.appendChild(item);
        var bar = item.querySelector('.ant-progress-bg');
        var progress = item.querySelector('.ant-progress');
        var close = message.loading('正在上传…', 0, 'upload');
        var xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        xhr.upload.onprogress = function (ev) {
          if (!ev.lengthComputable) return;
          bar.style.width = Math.round(ev.loaded / ev.total * 100) + '%';
        };
        function fail() {
          close();
          progress.classList.remove('ant-progress-status-active');
          progress.classList.add('ant-progress-status-exception');
          item.classList.add('ant-upload-list-item-error');
          message.error('上传失败，请稍后重试');
        }
        xhr.onload = function () {
          if (xhr.status >= 200 && xhr.status < 300) {
            close();
            bar.style.width = '100%';
            progress.classList.remove('ant-progress-status-active');
            progress.classList.add('ant-progress-status-success');
            message.success('上传成功');
          } else {
            fail();
          }
        };
        xhr.onerror = fail;
        var fd = new FormData();
        fd.append(input.name || 'file', file);
        xhr.send(fd);
        input.value = '';
      });
    });
  }

  function textOf(id) {
    var el = document.getElementById(id);
    if (!el) return '';
    var text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (text) el.setAttribute('hidden', '');
    return text;
  }

  function consumeFlashes() {
    var ok = textOf('flash-ok');
    var err = textOf('flash-err') || textOf('flash-late');
    if (err) message.error(err);
    if (!ok) return;
    if (document.body.getAttribute('data-page') === 'accounts') {
      notification.success({ message: '操作已完成', description: ok });
    } else {
      message.success(ok);
    }
  }

  function pageReady() {
    document.documentElement.classList.remove('ant-booting');
    var spin = document.getElementById('ant-page-spin');
    if (spin) {
      spin.setAttribute('aria-busy', 'false');
      spin.setAttribute('aria-hidden', 'true');
    }
  }

  function boot() {
    pageReady();
    consumeFlashes();
    bindForms();
    bindLogout();
    bindUploads();
  }

  window.addEventListener('pageshow', function (ev) {
    if (!ev.persisted) return;
    [].forEach.call(document.querySelectorAll('form'), function (form) {
      delete form.dataset.antSubmitting;
    });
    [].forEach.call(document.querySelectorAll('.ant-btn-loading'), function (btn) {
      setButtonLoading(btn, false);
    });
  });

  window.AntFeedback = {
    message: message,
    notification: notification,
    button: { loading: setButtonLoading },
    pageReady: pageReady
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
