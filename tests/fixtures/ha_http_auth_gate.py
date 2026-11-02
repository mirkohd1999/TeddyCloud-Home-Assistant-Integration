# SPDX-License-Identifier: Apache-2.0
# See LICENSE.home-assistant in this directory.
# Home Assistant Core HTTP authentication wrapper, extracted unchanged for
# contract tests on 2026-11-02. Source: homeassistant/helpers/http.py (dev).
# Home Assistant Core is licensed under Apache-2.0.
from __future__ import annotations

def request_handler_factory(
    hass: HomeAssistant, view: HomeAssistantView, handler: Callable
) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    """Wrap the handler classes."""
    is_coroutinefunction = inspect.iscoroutinefunction(handler)
    assert is_coroutinefunction or is_callback(handler), (
        "Handler should be a coroutine or a callback."
    )

    async def handle(request: web.Request) -> web.StreamResponse:
        """Handle incoming request."""
        if hass.is_stopping:
            return web.Response(status=HTTPStatus.SERVICE_UNAVAILABLE)

        authenticated = request.get(KEY_AUTHENTICATED, False)

        if view.requires_auth and not authenticated:
            # Import here to avoid circular dependency with network.py
            from .network import NoURLAvailableError, get_url  # noqa: PLC0415

            # Get the current request header to include as resource metadata
            # endpoint for RFC9728.
            try:
                url_prefix = get_url(hass, require_current_request=True)
            except NoURLAvailableError:
                # Omit header to avoid leaking configured URLs
                raise HTTPUnauthorized from None
            raise HTTPUnauthorized(
                headers={
                    "WWW-Authenticate": (
                        f'Bearer resource_metadata="{url_prefix}'
                        '/.well-known/oauth-protected-resource"'
                    )
                }
            )

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Serving %s to %s (auth: %s)",
                request.path,
                request.remote,
                authenticated,
            )

        # Set before the handler, decorators like RequestDataValidator read the body
        if view.max_body_size is not None:
            request._client_max_size = view.max_body_size  # noqa: SLF001

        try:
            if is_coroutinefunction:
                result = await handler(request, **request.match_info)
            else:
                result = handler(request, **request.match_info)
        except probatio.Invalid as err:
            raise HTTPBadRequest from err
        except exceptions.ServiceNotFound as err:
            raise HTTPInternalServerError from err
        except exceptions.Unauthorized as err:
            raise HTTPUnauthorized from err

        if isinstance(result, web.StreamResponse):
            # The method handler returned a ready-made Response, how nice of it
            return result

        status_code = HTTPStatus.OK
        if isinstance(result, tuple):
            result, status_code = result

        if isinstance(result, bytes):
            return web.Response(body=result, status=status_code)

        if isinstance(result, str):
            return web.Response(text=result, status=status_code)

        if result is None:
            return web.Response(body=b"", status=status_code)

        raise TypeError(
            f"Result should be None, string, bytes or StreamResponse. Got: {result}"
        )

    return handle
