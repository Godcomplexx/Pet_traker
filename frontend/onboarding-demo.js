(function () {
  'use strict';

  if (!window.api || typeof window.api.post !== 'function') return;

  const originalPost = window.api.post.bind(window.api);

  window.api.post = function postWithOnboardingDemo(path, body) {
    const isWorkspaceCreate = path === '/workspaces';
    const onboard = document.querySelector('#onboard.on');
    const demoToggle = document.querySelector('#obDemoData');

    if (
      isWorkspaceCreate &&
      onboard &&
      body &&
      !Object.prototype.hasOwnProperty.call(body, 'with_demo_data')
    ) {
      return originalPost(path, {
        ...body,
        with_demo_data: demoToggle ? demoToggle.checked : true,
      });
    }

    return originalPost(path, body);
  };
})();
